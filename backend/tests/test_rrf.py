"""RRF 融合纯逻辑单元测试：只测排名融合，不触数据库、不触发检索。"""
import sys
from pathlib import Path

# 保证从 backend/ 目录直接跑 pytest 时能 import 到 app 包
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.retriever import RetrievedChunk, rrf_fuse


def make_chunk(chunk_id: int, score: float = 0.0) -> RetrievedChunk:
    """构造测试用检索片段。"""
    return RetrievedChunk(
        chunk_id=chunk_id,
        document_id=1,
        document_title="测试文档",
        seq=chunk_id,
        content=f"内容{chunk_id}",
        score=score,
    )


def test_top_of_both_rankings_ranks_first():
    """双榜单第一名: 两路都排第一的块，融合后应居首。"""
    ranking_a = [make_chunk(1), make_chunk(2), make_chunk(3)]
    ranking_b = [make_chunk(1), make_chunk(4), make_chunk(5)]
    fused = rrf_fuse([ranking_a, ranking_b])
    assert fused[0].chunk_id == 1


def test_dedup_by_chunk_id():
    """去重: 同一块出现在多个榜单时，融合结果中只保留一份。"""
    ranking_a = [make_chunk(1), make_chunk(2)]
    ranking_b = [make_chunk(3), make_chunk(1)]
    fused = rrf_fuse([ranking_a, ranking_b])
    ids = [c.chunk_id for c in fused]
    assert sorted(ids) == [1, 2, 3]
    assert len(ids) == len(set(ids))


def test_tie_scores_keep_stable_order():
    """平分: 各块 RRF 得分相同时，排序结果应确定且稳定（首现顺序优先）。"""
    ranking_a = [make_chunk(1), make_chunk(2)]
    ranking_b = [make_chunk(3), make_chunk(4)]
    first = [c.chunk_id for c in rrf_fuse([ranking_a, ranking_b])]
    second = [c.chunk_id for c in rrf_fuse([ranking_a, ranking_b])]
    assert first == second  # 相同输入多次运行结果一致
    assert first[0] == 1  # 平分时先出现的块排在前
    assert sorted(first) == [1, 2, 3, 4]


def test_empty_rankings_no_error():
    """空榜单: 空输入与全空榜单都不报错，返回空列表。"""
    assert rrf_fuse([]) == []
    assert rrf_fuse([[], []]) == []
