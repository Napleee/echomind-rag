"""Embedding 服务：sentence-transformers 本地模型单例封装。

首次调用 get_embedder() 才加载模型（懒加载），用 threading.Lock 防止并发重复加载。
"""
import logging
import os
import threading

import numpy as np

from app.core.config import get_settings

settings = get_settings()
# 必须在导入 sentence_transformers 之前设置：走国内镜像，避免 HuggingFace 直连失败
os.environ.setdefault("HF_ENDPOINT", settings.hf_endpoint)

from sentence_transformers import SentenceTransformer  # noqa: E402  需在环境变量设置之后导入

logger = logging.getLogger(__name__)

# bge 系列查询侧指令前缀，可显著提升检索召回
_QUERY_INSTRUCTION = "为这个句子生成表示以用于检索相关文章："


class Embedder:
    """封装 SentenceTransformer 的文档向量 / 查询向量接口。"""

    def __init__(self, model: SentenceTransformer) -> None:
        self._model = model

    def embed_documents(self, texts: list[str]) -> np.ndarray:
        """批量生成文档向量（已 L2 归一化），返回 numpy 数组。"""
        if not texts:
            dim = self._model.get_sentence_embedding_dimension() or 0
            return np.zeros((0, dim), dtype=np.float32)
        vectors = self._model.encode(
            list(texts),
            batch_size=32,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return np.asarray(vectors, dtype=np.float32)

    def embed_query(self, text: str) -> np.ndarray:
        """查询文本加 bge 指令前缀后单条编码并 L2 归一化。"""
        vector = self._model.encode(
            [_QUERY_INSTRUCTION + text],
            batch_size=1,
            normalize_embeddings=True,
            show_progress_bar=False,
        )[0]
        vec = np.asarray(vector, dtype=np.float32)
        norm = float(np.linalg.norm(vec))
        return vec / norm if norm > 0 else vec


_embedder: Embedder | None = None
_embedder_lock = threading.Lock()


def get_embedder() -> Embedder:
    """获取 Embedder 单例；首次调用时加载模型（device="cpu"）。"""
    global _embedder
    if _embedder is None:
        with _embedder_lock:
            if _embedder is None:  # 双重检查，防止并发重复加载
                logger.info("加载 embedding 模型: %s", settings.embedding_model)
                try:
                    model = SentenceTransformer(
                        settings.embedding_model,
                        device="cpu",
                        show_progress_bar=False,
                    )
                except TypeError:
                    # 旧版本构造函数不支持 show_progress_bar 参数
                    model = SentenceTransformer(settings.embedding_model, device="cpu")
                _embedder = Embedder(model)
                logger.info("embedding 模型加载完成")
    return _embedder
