"""精排（rerank）: 基于 CrossEncoder 对 (query, chunk 内容) 打分重排。

懒加载模型: settings.enable_rerank 为 False 时完全不加载。
"""
from __future__ import annotations

import logging
import os
import threading
from dataclasses import replace
from typing import Any, Optional

from app.core.config import get_settings
from app.services.retriever import RetrievedChunk

logger = logging.getLogger(__name__)

_cross_encoder: Optional[Any] = None
_lock = threading.Lock()


def _get_cross_encoder() -> Any:
    """懒加载 CrossEncoder 单例。"""
    global _cross_encoder
    with _lock:
        if _cross_encoder is None:
            # 延迟导入重依赖，且保证未开启 rerank 时不会加载
            from sentence_transformers import CrossEncoder

            settings = get_settings()
            os.environ.setdefault("HF_ENDPOINT", settings.hf_endpoint)  # 国内镜像
            logger.info("加载 rerank 模型: %s", settings.rerank_model)
            _cross_encoder = CrossEncoder(settings.rerank_model)
        return _cross_encoder


def rerank(query: str, chunks: list[RetrievedChunk], top_k: int) -> list[RetrievedChunk]:
    """对候选块重排，返回前 top_k 条（score 覆盖为 rerank 得分）。

    settings.enable_rerank 为 False 时跳过模型，直接截断。
    """
    settings = get_settings()
    if not settings.enable_rerank or not chunks:
        return list(chunks[:top_k])
    model = _get_cross_encoder()
    pairs = [(query, c.content) for c in chunks]
    scores = model.predict(pairs)
    ranked = sorted(
        zip(chunks, scores), key=lambda t: (-float(t[1]), t[0].chunk_id)
    )[:top_k]
    return [replace(c, score=round(float(s), 4)) for c, s in ranked]
