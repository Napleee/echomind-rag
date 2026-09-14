"""LLM 流式生成: OpenAI 兼容协议；未配置 API key 时进入 mock 模式。"""
from __future__ import annotations

import logging
from typing import Any, Iterator, Optional

import openai

from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "你是一个严谨的中文文档问答助手。请只依据用户提供的资料回答问题；"
    "如果资料中没有相关信息，必须明确回答「资料中未提及」，禁止编造或臆测。"
    "回答末尾用 [编号] 标注你引用了哪些资料，例如 [1][3]。"
)

_client: Optional[openai.OpenAI] = None


def _get_client(settings: Settings) -> openai.OpenAI:
    """懒加载 OpenAI 兼容客户端单例。"""
    global _client
    if _client is None:
        _client = openai.OpenAI(base_url=settings.llm_base_url, api_key=settings.llm_api_key)
    return _client


def _build_user_content(question: str, context_blocks: list[str]) -> str:
    """user 消息: 编号资料块 + 问题（context_blocks 自带编号与前缀）。"""
    joined = "\n\n".join(context_blocks) if context_blocks else "（无）"
    return f"资料：\n{joined}\n\n问题：{question}"


def _mock_stream(context_blocks: list[str]) -> Iterator[str]:
    """mock 模式: 不调 LLM，回显检索资料摘要，分 2~4 次 yield。"""
    header = (
        "【mock 模式】未配置 LLM_API_KEY，以下为检索到的资料摘要，"
        "配置后可得到真正的生成回答。\n\n"
    )
    if context_blocks:
        summary = "\n\n".join(context_blocks)
        if len(summary) > 800:
            summary = summary[:797] + "……"  # 含省略号总长不超过 800 字
        # 按 ~300 字切成最多 3 段，加上 header 共 2~4 次 yield
        pieces = [summary[i : i + 300] for i in range(0, len(summary), 300)][:3]
    else:
        pieces = ["（未检索到相关资料）"]
    yield header
    for piece in pieces:
        yield piece


def _create_stream(client: openai.OpenAI, settings: Settings, user_content: str) -> Any:
    """发起流式补全请求；stream_options 不被部分厂商支持时降级重试。"""
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]
    try:
        return client.chat.completions.create(
            model=settings.llm_model,
            messages=messages,
            stream=True,
            stream_options={"include_usage": True},
        )
    except Exception:  # noqa: BLE001 兼容不支持 stream_options 的厂商
        logger.debug("stream_options 调用失败，降级为普通流式请求")
        return client.chat.completions.create(
            model=settings.llm_model,
            messages=messages,
            stream=True,
        )


def stream_answer(question: str, context_blocks: list[str]) -> Iterator[str]:
    """流式生成回答，逐段 yield 增量文本。"""
    settings = get_settings()
    if not settings.llm_api_key:
        yield from _mock_stream(context_blocks)
        return

    client = _get_client(settings)
    stream = _create_stream(client, settings, _build_user_content(question, context_blocks))
    usage_logged = False
    try:
        for chunk in stream:
            usage = getattr(chunk, "usage", None)  # include_usage 时最后一个 chunk 携带
            if usage is not None and not usage_logged:
                logger.info(
                    "LLM usage: prompt=%s completion=%s",
                    getattr(usage, "prompt_tokens", None),
                    getattr(usage, "completion_tokens", None),
                )
                usage_logged = True
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            content = getattr(delta, "content", None)
            if content:
                yield content
    finally:
        close = getattr(stream, "close", None)
        if close is not None:
            close()
