"""对话问答 API: SSE 流式返回（sources → token… → done / error）。

链路（含阶段5缓存优化）:
    1. 完整回答缓存命中 → 直接回放（含 cached 标记），跳过检索与生成
    2. 检索结果缓存命中 → 跳过向量化/检索/重排，直接进大模型
    3. 均未命中 → 完整链路: embedding → 混合检索(可选重排) → 流式生成，并写两层缓存
"""
from __future__ import annotations

import json
import logging
import time
from typing import Iterator, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import SessionLocal, get_db
from app.models import Conversation, Message
from app.schemas import ChatRequest, ConversationOut, MessageOut, SourceOut
from app.services import cache, retriever
from app.services.embedder import get_embedder
from app.services.llm import stream_answer

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["chat"])

_ANSWER_REPLAY_SLICE = 100  # 回放缓存回答时每条 token 事件的字符数


def _sse(event: str, data: dict) -> str:
    """构造一条 SSE 事件: 一行 event、一行 data（单行 JSON）、一个空行。"""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _generate(conversation_id: int, question: str, top_k: Optional[int]) -> Iterator[str]:
    """SSE 生成器: 检索 → sources → 流式 token → done；异常时以 error 终结，不发送 done。"""
    start = time.perf_counter()
    full_text = ""
    sources_payload: list[dict] = []

    def _latency_ms() -> int:
        return int((time.perf_counter() - start) * 1000)

    def _persist() -> None:
        """落库 assistant 消息（保留部分产出，断流也有记录）。"""
        if not full_text:
            # 未产出任何正文（检索/LLM 即失败）时不落库，避免历史里出现空气泡
            return
        db = SessionLocal()
        try:
            db.add(
                Message(
                    conversation_id=conversation_id,
                    role="assistant",
                    content=full_text,
                    sources=sources_payload or None,
                    latency_ms=_latency_ms(),
                )
            )
            db.commit()
        except Exception:  # noqa: BLE001 落库失败不影响已发出的响应
            db.rollback()
            logger.exception("assistant 消息落库失败")
        finally:
            db.close()

    # ---- 第一层: 完整回答缓存命中 → 回放，跳过检索与生成 ----
    cached_answer = cache.get_cached_answer(question)
    if cached_answer:
        retrieval = cache.get_cached_retrieval(question)
        if retrieval:
            sources_payload = retrieval["sources"]
        if sources_payload:
            yield _sse("sources", {"sources": sources_payload})
        full_text = cached_answer
        for i in range(0, len(full_text), _ANSWER_REPLAY_SLICE):
            yield _sse("token", {"delta": full_text[i : i + _ANSWER_REPLAY_SLICE]})
        yield _sse(
            "done",
            {"conversation_id": conversation_id, "latency_ms": _latency_ms(), "cached": True},
        )
        _persist()
        return

    try:
        context_blocks: list[str]
        retrieval = cache.get_cached_retrieval(question)
        if retrieval:
            # ---- 第二层: 检索结果缓存命中 → 跳过 embedding/检索/重排 ----
            sources_payload = retrieval["sources"]
            context_blocks = retrieval["context_blocks"]
        else:
            # 1) 问题转向量（embedding 由调用方完成，retriever 不碰 embedder）
            query_embedding = get_embedder().embed_query(question)
            # 2) 向量 + BM25 + RRF（可选 rerank）；top_k 作为最终条数透传，缺省用 final_top_k
            chunks = retriever.search(question, query_embedding, final_k=top_k)
            sources_payload = [
                SourceOut(
                    chunk_id=c.chunk_id,
                    document_id=c.document_id,
                    document_title=c.document_title,
                    seq=c.seq,
                    score=round(c.score, 4),
                    snippet=c.content[:150],
                ).model_dump()
                for c in chunks
            ]
            context_blocks = [
                f"资料{i}（来自 {c.document_title} 第{c.seq + 1}段）: {c.content}"
                for i, c in enumerate(chunks, start=1)
            ]
            cache.cache_retrieval(question, sources_payload, context_blocks)

        # 3) 先发 sources 溯源事件
        yield _sse("sources", {"sources": sources_payload})
        # 4) 流式生成回答
        for delta in stream_answer(question, context_blocks):
            full_text += delta
            yield _sse("token", {"delta": delta})
    except GeneratorExit:
        # 客户端断开: 保存已产出内容后原样退出
        _persist()
        raise
    except Exception as exc:  # noqa: BLE001 转为 error 事件
        logger.exception("问答生成失败")
        yield _sse("error", {"message": f"生成回答失败：{exc}"})
        _persist()  # 保留部分产出（无正文时 _persist 内部会跳过）
        return  # error 是异常路径的终结事件，不再发送 done

    # 成功完成: 写完整回答缓存，发 done
    if full_text:
        cache.cache_answer(question, full_text)
    yield _sse("done", {"conversation_id": conversation_id, "latency_ms": _latency_ms()})
    _persist()


@router.post("/chat")
def chat(
    req: ChatRequest, request: Request, db: Session = Depends(get_db)
) -> StreamingResponse:
    """提问: 创建/复用会话并落库 user 消息，再以 SSE 流式返回回答。

    按 IP 固定窗口限流（Redis 降级时直通）。
    """
    client_ip = request.client.host if request.client else "unknown"
    allowed, retry_after = cache.rate_limit(client_ip)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail=f"提问太频繁，请约 {retry_after} 秒后再试。",
            headers={"Retry-After": str(retry_after)},
        )

    # 会话不存在则创建，标题取问题前 50 字
    if req.conversation_id is not None:
        conversation = db.get(Conversation, req.conversation_id)
        if conversation is None:
            raise HTTPException(status_code=404, detail="会话不存在")
    else:
        conversation = Conversation(title=req.question[:50])
        db.add(conversation)
        db.commit()
        db.refresh(conversation)

    # 先落库 user 消息
    db.add(Message(conversation_id=conversation.id, role="user", content=req.question))
    db.commit()

    return StreamingResponse(
        _generate(conversation.id, req.question, req.top_k),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/conversations", response_model=list[ConversationOut])
def list_conversations(db: Session = Depends(get_db)) -> list[ConversationOut]:
    """会话列表: 最新 50 条。"""
    rows = db.scalars(
        select(Conversation).order_by(Conversation.id.desc()).limit(50)
    ).all()
    return [ConversationOut.model_validate(c, from_attributes=True) for c in rows]


@router.get("/conversations/{conversation_id}/messages", response_model=list[MessageOut])
def list_messages(conversation_id: int, db: Session = Depends(get_db)) -> list[MessageOut]:
    """会话消息: 按 id 升序；会话不存在返回 404。"""
    if db.get(Conversation, conversation_id) is None:
        raise HTTPException(status_code=404, detail="会话不存在")
    rows = db.scalars(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.id.asc())
    ).all()
    return [MessageOut.model_validate(m, from_attributes=True) for m in rows]
