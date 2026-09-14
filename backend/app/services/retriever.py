"""混合检索：向量召回 + BM25 召回 + RRF 融合（可选 rerank）。

注意: 本模块不 import embedder —— embedding 由调用方完成后传入，
保证纯检索逻辑可独立测试。
"""
from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from typing import Optional

import jieba
from rank_bm25 import BM25Okapi
from sqlalchemy import select

from app.core.config import get_settings
from app.core.db import SessionLocal
from app.models import Chunk, Document

logger = logging.getLogger(__name__)


@dataclass
class RetrievedChunk:
    """检索结果条目（跨模块通用载体）。"""

    chunk_id: int
    document_id: int
    document_title: str
    seq: int
    content: str
    score: float = 0.0


def _to_list(query_embedding) -> list[float]:
    """兼容 numpy ndarray / list 等输入，转成 float 列表。"""
    if hasattr(query_embedding, "tolist"):
        return [float(x) for x in query_embedding.tolist()]
    return [float(x) for x in query_embedding]


def vector_search(query_embedding, k: int) -> list[RetrievedChunk]:
    """向量检索: 按余弦距离升序取前 k 条，score = 1 - distance。"""
    if k <= 0:
        return []
    emb = _to_list(query_embedding)
    dist_expr = Chunk.embedding.cosine_distance(emb)  # pgvector Vector 自带方法
    with SessionLocal() as db:
        rows = (
            db.execute(
                select(Chunk, Document.title, dist_expr)
                .join(Document, Chunk.document_id == Document.id)
                .where(Chunk.embedding.isnot(None))
                .order_by(dist_expr.asc(), Chunk.id.asc())
                .limit(k)
            )
            .all()
        )
    results: list[RetrievedChunk] = []
    for chunk, title, distance in rows:
        score = 1.0 - float(distance)
        results.append(
            RetrievedChunk(
                chunk_id=chunk.id,
                document_id=chunk.document_id,
                document_title=title,
                seq=chunk.seq,
                content=chunk.content,
                score=score,
            )
        )
    return results


def _tokenize(text: str) -> list[str]:
    """jieba 分词，去掉纯空白 token。"""
    return [t for t in jieba.lcut(text) if t.strip()]


class BM25Index:
    """进程内 BM25 索引（构建时一次性读取全部 Chunk）。"""

    def __init__(
        self,
        chunk_ids: list[int],
        document_ids: list[int],
        titles: list[str],
        seqs: list[int],
        contents: list[str],
        bm25: Optional[BM25Okapi],
    ) -> None:
        self.chunk_ids = chunk_ids
        self.document_ids = document_ids
        self.titles = titles
        self.seqs = seqs
        self.contents = contents
        self.bm25 = bm25

    @classmethod
    def build(cls) -> "BM25Index":
        """读取全部 Chunk 建索引；库为空时 bm25 为 None。"""
        chunk_ids: list[int] = []
        document_ids: list[int] = []
        titles: list[str] = []
        seqs: list[int] = []
        corpus: list[list[str]] = []
        contents: list[str] = []
        with SessionLocal() as db:
            rows = db.execute(
                select(Chunk.id, Chunk.document_id, Chunk.content, Chunk.seq, Document.title)
                .join(Document, Chunk.document_id == Document.id)
                .order_by(Chunk.id.asc())
            ).all()
        for cid, doc_id, content, seq, title in rows:
            tokens = _tokenize(content)
            if not tokens:
                continue  # 纯空白块无法参与 BM25，跳过
            chunk_ids.append(cid)
            document_ids.append(doc_id)
            titles.append(title)
            seqs.append(seq)
            contents.append(content)
            corpus.append(tokens)
        bm25 = BM25Okapi(corpus) if corpus else None
        logger.info("BM25 索引构建完成: %d 个块", len(chunk_ids))
        return cls(chunk_ids, document_ids, titles, seqs, contents, bm25)

    def search(self, query: str, k: int) -> list[RetrievedChunk]:
        """按 BM25 分数取前 k 条；索引为空返回空列表。"""
        if self.bm25 is None or not self.chunk_ids or k <= 0:
            return []
        scores = self.bm25.get_scores(_tokenize(query))
        order = sorted(range(len(scores)), key=lambda i: (-float(scores[i]), self.chunk_ids[i]))
        results: list[RetrievedChunk] = []
        for i in order[:k]:
            results.append(
                RetrievedChunk(
                    chunk_id=self.chunk_ids[i],
                    document_id=self.document_ids[i],
                    document_title=self.titles[i],
                    seq=self.seqs[i],
                    content=self.contents[i],
                    score=float(scores[i]),
                )
            )
        return results


# ---- 模块级缓存（进程内单例） ----
_bm25_index: Optional[BM25Index] = None
_bm25_lock = threading.Lock()


def _get_bm25_index() -> BM25Index:
    global _bm25_index
    with _bm25_lock:
        if _bm25_index is None:
            _bm25_index = BM25Index.build()
        return _bm25_index


def refresh_bm25() -> None:
    """重建 BM25 索引（文档入库/删除/重建索引后由入库方调用）。"""
    global _bm25_index
    with _bm25_lock:
        _bm25_index = BM25Index.build()


def bm25_search(query: str, k: int) -> list[RetrievedChunk]:
    """BM25 检索入口: 索引未建则先建。"""
    if k <= 0:
        return []
    return _get_bm25_index().search(query, k)


def rrf_fuse(rankings: list[list[RetrievedChunk]], k: int = 60) -> list[RetrievedChunk]:
    """Reciprocal Rank Fusion: 每个榜单第 rank 名贡献 1/(k+rank)。

    按 chunk_id 去重累加，RRF 得分降序，同分时 chunk_id 小者优先；
    返回的 score 字段填 RRF 得分。
    """
    scores: dict[int, float] = {}
    first_seen: dict[int, RetrievedChunk] = {}
    for ranking in rankings:
        for rank, chunk in enumerate(ranking, start=1):
            scores[chunk.chunk_id] = scores.get(chunk.chunk_id, 0.0) + 1.0 / (k + rank)
            first_seen.setdefault(chunk.chunk_id, chunk)
    fused: list[RetrievedChunk] = []
    for cid, score in scores.items():
        base = first_seen[cid]
        fused.append(
            RetrievedChunk(
                chunk_id=base.chunk_id,
                document_id=base.document_id,
                document_title=base.document_title,
                seq=base.seq,
                content=base.content,
                score=score,
            )
        )
    fused.sort(key=lambda c: (-c.score, c.chunk_id))
    return fused


def search(
    question: str, query_embedding, final_k: Optional[int] = None
) -> list[RetrievedChunk]:
    """检索编排入口: 向量 + BM25 两路召回 → RRF 融合 → 可选 rerank。

    final_k: 最终返回条数；缺省用 settings.final_top_k（供 API 透传客户端 top_k 覆盖）。
    """
    settings = get_settings()
    k = settings.final_top_k if final_k is None else final_k
    rankings: list[list[RetrievedChunk]] = [
        vector_search(query_embedding, settings.vector_top_k),
        bm25_search(question, settings.bm25_top_k),
    ]
    fused = rrf_fuse(rankings, k=settings.rrf_k)
    if settings.enable_rerank:
        # 延迟导入，避免与 reranker 模块循环依赖
        from app.services.reranker import rerank

        # 只精排融合后前 rerank_candidates 名: 重排是为了精确切 top-k，
        # 对 40 个候选全量精排只增加 CPU 延迟，不改善最终 top-k 质量
        return rerank(question, fused[: settings.rerank_candidates], k)
    return fused[:k]
