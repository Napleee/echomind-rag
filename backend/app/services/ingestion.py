"""文档入库管线：解析 → 切块 → 向量化 → 批量落库 → 刷新 BM25 索引。

任何异常都只落到 Document.status="error"，不向外抛出（后台任务安全）。
"""
import logging
from pathlib import Path

from app.core.config import get_settings
from app.core.db import SessionLocal
from app.models import Chunk, Document
from app.services.chunker import chunk_text
from app.services.embedder import get_embedder
from app.services.parsers import parse_file

logger = logging.getLogger(__name__)


def run_ingestion(document_id: int, file_path: str, source_type: str) -> None:
    """对指定文档执行完整入库管线（自开会话，供后台任务调用）。"""
    settings = get_settings()
    db = SessionLocal()
    try:
        doc = db.get(Document, document_id)
        if doc is None:
            logger.error("入库中止：文档不存在 id=%s", document_id)
            return

        # 1. 解析原文
        text = parse_file(Path(file_path), source_type)
        # 2. 切块
        chunks = chunk_text(
            text,
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
        )
        # 3. 向量化（一次性编码全部块）
        vectors = get_embedder().embed_documents(chunks)

        # 4. 清掉旧块（reindex 场景可能残留），再批量插入
        from sqlalchemy import delete

        db.execute(delete(Chunk).where(Chunk.document_id == document_id))
        for seq, (content, vec) in enumerate(zip(chunks, vectors)):
            db.add(
                Chunk(
                    document_id=document_id,
                    seq=seq,
                    content=content,
                    embedding=vec.tolist(),
                )
            )

        # 5. 更新文档状态
        doc.chunk_count = len(chunks)
        doc.status = "ready"
        doc.error = None
        db.commit()
        logger.info("文档入库完成 id=%s chunks=%d", document_id, len(chunks))
    except Exception as e:  # noqa: BLE001  管线失败只落状态，不外抛
        db.rollback()
        logger.exception("文档入库失败 id=%s", document_id)
        try:
            failed = db.get(Document, document_id)
            if failed is not None:
                failed.status = "error"
                failed.error = str(e)[:2000]
                db.commit()
        except Exception:  # noqa: BLE001
            db.rollback()
            logger.exception("写入失败状态时出错 id=%s", document_id)
        return
    finally:
        db.close()

    # 6. 成功结束后刷新 BM25 索引（函数内 import 避免循环依赖）
    from app.services.retriever import refresh_bm25

    try:
        refresh_bm25()
    except Exception:  # noqa: BLE001  索引刷新失败不影响入库结果
        logger.exception("刷新 BM25 索引失败 id=%s", document_id)
