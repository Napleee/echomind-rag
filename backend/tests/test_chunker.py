"""chunker 纯逻辑单元测试：只测切分函数本身，不触数据库、不下载模型。"""
import sys
from pathlib import Path

# 保证从 backend/ 目录直接跑 pytest 时能 import 到 app 包
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.chunker import chunk_text


def test_normal_split_and_chunk_size_limit():
    """多句正常文本: 能切出多块，且每块长度不超过 chunk_size、内容非空。"""
    text = "。".join(
        f"这是第{i}句测试内容，包含一些中文句子用来验证切块行为是否稳定" for i in range(80)
    ) + "。"
    chunks = chunk_text(text, chunk_size=500, chunk_overlap=50)
    assert len(chunks) >= 2
    assert all(isinstance(c, str) and 0 < len(c) <= 500 for c in chunks)
    # 切分不丢内容：首块应从原文开头开始
    assert text[:20] in chunks[0]


def test_long_text_without_punctuation_hard_split():
    """超长无标点文本: 强制走硬切路径，块长不超过上限。"""
    text = "0123456789" * 150  # 1500 字符，无任何标点
    chunks = chunk_text(text, chunk_size=500, chunk_overlap=50)
    assert len(chunks) >= 3
    assert all(len(c) <= 500 for c in chunks)
    # 硬切从原文头部开始
    assert chunks[0] == text[:500]


def test_empty_text_returns_empty_list():
    """空文本: 返回空列表而不是报错或单块空串。"""
    assert chunk_text("", chunk_size=500, chunk_overlap=50) == []
    assert chunk_text("") == []  # 默认参数同样成立


def test_adjacent_chunks_overlap():
    """相邻块重叠: 后一块的开头应复用前一块结尾的 overlap 个字符。"""
    text = "0123456789" * 150  # 无标点，必走硬切路径
    overlap = 50
    chunks = chunk_text(text, chunk_size=500, chunk_overlap=overlap)
    assert len(chunks) >= 3
    for prev, nxt in zip(chunks, chunks[1:]):
        assert nxt[:overlap] == prev[-overlap:]


def test_short_text_kept_as_single_chunk():
    """短文本（小于 chunk_size）: 不切分，内容完整保留。"""
    text = "只有一句话的短文本。"
    chunks = chunk_text(text, chunk_size=500, chunk_overlap=50)
    assert len(chunks) == 1
    assert "一句话" in chunks[0]
