"""切块大小对比实验：在内存中重建索引，对比不同 chunk_size 下的检索质量与开销。

不写入生产 chunks 表——解析与切块直接从原始文档进行，向量检索用 numpy 精确计算
（实验规模下与 pgvector 近似结果，避免反复重建数据库索引）。

用法（在 backend/ 目录下，需已启动数据库并入库过文档）:
    python -m eval.run_chunk_experiment              # 默认对比 300 / 500 / 800
    python -m eval.run_chunk_experiment --sizes 200,300,500,800,1200
    python -m eval.run_chunk_experiment --k 5

输出: 每个尺寸下的 chunk 数、recall@k、MRR、入库耗时（切块+向量化）、平均检索延迟。
"""
import argparse
import sys
import time
from pathlib import Path

import numpy as np

# 保证从任意工作目录运行都能 import 到 app 包
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from eval.run_eval import load_questions  # noqa: E402  复用问题集加载逻辑

QUESTIONS_FILE = Path(__file__).resolve().parent / "questions.yaml"

RRF_K = 60  # 与线上 rrf_k 保持一致


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="EchoMind 切块大小对比实验")
    parser.add_argument(
        "--sizes",
        type=str,
        default="300,500,800",
        help="逗号分隔的 chunk_size 列表（默认 300,500,800）",
    )
    parser.add_argument("--k", type=int, default=5, help="判定命中的检索条数（默认 5）")
    parser.add_argument("--limit", type=int, default=None, help="只评估前 N 道题")
    return parser.parse_args()


def load_corpus() -> list[tuple[str, str]]:
    """读取知识库中全部就绪文档的原始文本，返回 [(title, text), ...]。"""
    from app.core.db import SessionLocal
    from app.models import Document
    from app.services.parsers import parse_file

    docs: list[tuple[str, str]] = []
    with SessionLocal() as db:
        rows = db.query(Document).filter(Document.status == "ready").all()
        if not rows:
            print("[错误] 知识库为空，请先上传文档再运行实验。")
            sys.exit(1)
        for row in rows:
            path = Path(row.file_path)
            if not path.exists():
                print(f"[警告] 原始文件缺失，跳过: {row.title} ({row.file_path})")
                continue
            docs.append((row.title, parse_file(path, row.source_type)))
    return docs


def rrf_fuse(rankings: list[list[int]], k: int = RRF_K) -> list[int]:
    """RRF 融合多路排名（元素为 chunk 下标），返回按融合分降序的下标列表。"""
    scores: dict[int, float] = {}
    for ranking in rankings:
        for rank, idx in enumerate(ranking, 1):
            scores[idx] = scores.get(idx, 0.0) + 1.0 / (k + rank)
    return sorted(scores, key=lambda i: (-scores[i], i))


def evaluate_size(
    corpus: list[tuple[str, str]],
    questions: list[dict],
    chunk_size: int,
    top_k: int,
    embedder,
) -> dict:
    """在给定 chunk_size 下重建内存索引并评估，返回指标 dict。"""
    from app.services import chunker
    from rank_bm25 import BM25Okapi

    import jieba

    overlap = max(10, chunk_size // 10)  # 重叠取 10%，与线上 500/50 的比例一致

    # ---- 入库阶段: 切块 + 向量化（计时）----
    t0 = time.perf_counter()
    texts: list[str] = []
    for _, doc_text in corpus:
        texts.extend(chunker.chunk_text(doc_text, chunk_size=chunk_size, chunk_overlap=overlap))
    embeddings = (
        embedder.embed_documents(texts) if texts else np.zeros((0, 1), dtype="float32")
    )
    # BM25 语料（与线上同款 jieba 分词）
    tokenized = [jieba.lcut(t) for t in texts]
    bm25 = BM25Okapi(tokenized) if texts else None
    index_ms = (time.perf_counter() - t0) * 1000

    # ---- 查询阶段 ----
    hits = 0
    mrr_sum = 0.0
    total_ms = 0.0
    for item in questions:
        question = item["question"]
        keywords = item["expected_keywords"]
        qe = embedder.embed_query(question)
        t0 = time.perf_counter()
        # 向量路: 余弦相似度（embedder 已 L2 归一化，内积即余弦）
        sims = embeddings @ qe
        vec_ranking = np.argsort(-sims)[:20].tolist()
        # BM25 路（get_scores 只算一次，排序用下标取值）
        bm_ranking = []
        if bm25 is not None:
            bm_scores = bm25.get_scores(jieba.lcut(question))
            bm_ranking = sorted(range(len(texts)), key=lambda i: -bm_scores[i])[:20]
        fused = rrf_fuse([vec_ranking, bm_ranking])[:top_k]
        total_ms += (time.perf_counter() - t0) * 1000

        first_hit_rank = 0
        for rank, idx in enumerate(fused, 1):
            if any(kw in texts[idx] for kw in keywords):
                first_hit_rank = rank
                break
        if first_hit_rank:
            hits += 1
            mrr_sum += 1.0 / first_hit_rank

    n = len(questions)
    avg_len = sum(len(t) for t in texts) / max(len(texts), 1)
    return {
        "chunk_size": chunk_size,
        "chunks": len(texts),
        "avg_len": avg_len,
        "recall": hits / n,
        "mrr": mrr_sum / n,
        "index_ms": index_ms,
        "query_ms": total_ms / n,
    }


def main() -> None:
    args = parse_args()
    sizes = [int(s) for s in args.sizes.split(",") if s.strip()]

    questions = load_questions(QUESTIONS_FILE)
    if args.limit is not None:
        questions = questions[: args.limit]
    if not questions:
        print("[错误] 问题集为空。")
        sys.exit(1)

    corpus = load_corpus()
    print(f"语料 {len(corpus)} 份文档 / {len(questions)} 道题 / hybrid 策略 / k={args.k}")
    print(f"语料总字符数: {sum(len(t) for _, t in corpus)}")
    print("-" * 76)
    print(f"{'size':>6} {'chunks':>7} {'均长':>6} {'recall@k':>9} {'MRR':>6} {'入库ms':>8} {'检索ms':>8}")
    print("-" * 76)

    from app.services.embedder import get_embedder

    embedder = get_embedder()
    for size in sizes:
        r = evaluate_size(corpus, questions, size, args.k, embedder)
        print(
            f"{r['chunk_size']:>6} {r['chunks']:>7} {r['avg_len']:>6.0f} "
            f"{r['recall']:>8.1%} {r['mrr']:>6.3f} {r['index_ms']:>8.0f} {r['query_ms']:>8.1f}"
        )


if __name__ == "__main__":
    main()
