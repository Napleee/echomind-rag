"""切块服务：纯 Python 实现，零第三方依赖。

流程：统一换行 → 按空行切段（段内逐级降级细分）→ 贪心合并相邻小段 → 丢弃全空白块。
硬性约束：返回的每一块长度都必须 ≤ chunk_size。
"""
import logging

logger = logging.getLogger(__name__)

# 中英文句末标点
# 中英文句末标点
_SENTENCE_ENDINGS = "。！？；!?"


def _normalize(text: str) -> str:
    """统一换行符为 LF，并把连续空行压缩为一个空行。"""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.rstrip() for line in text.split("\n")]
    collapsed: list[str] = []
    blank_run = 0
    for line in lines:
        if line == "":
            blank_run += 1
            if blank_run <= 1:  # 只保留一个空行
                collapsed.append(line)
        else:
            blank_run = 0
            collapsed.append(line)
    return "\n".join(collapsed).strip()


def _hard_split(text: str, chunk_size: int, overlap: int) -> list[str]:
    """按字符硬切，相邻块保留 overlap 字符重叠，每块 ≤ chunk_size。"""
    pieces: list[str] = []
    start = 0
    step = max(1, chunk_size - overlap)  # 防御 overlap ≥ chunk_size 的配置错误
    while start < len(text):
        pieces.append(text[start : start + chunk_size])
        if start + chunk_size >= len(text):
            break
        start += step
    return pieces


def _split_sentences(text: str) -> list[str]:
    """按中英文句末符切段，句末标点保留在句尾。"""
    sentences: list[str] = []
    buf: list[str] = []
    for ch in text:
        buf.append(ch)
        if ch in _SENTENCE_ENDINGS:
            sentences.append("".join(buf))
            buf = []
    tail = "".join(buf)
    if tail.strip():
        sentences.append(tail)
    return [s for s in sentences if s.strip()]


def chunk_text(text: str, chunk_size: int = 500, chunk_overlap: int = 50) -> list[str]:
    """把文本切成若干 ≤ chunk_size 的块。

    第一步：CRLF/CR 统一为 LF，连续空行压缩为一个空行；
    第二步：先按空行切段；单段仍超长时依次降级为「按单个换行切 → 按句末符切 →
            按字符硬切（硬切相邻块保留 chunk_overlap 重叠）」；
    第三步：贪心合并相邻小段（以换行符连接）直到接近 chunk_size；
    第四步：丢弃全空白块。
    """
    if chunk_size < 1:
        raise ValueError(f"chunk_size 必须为正整数，收到: {chunk_size}")
    overlap = max(0, min(chunk_overlap, chunk_size - 1))

    # 第一步：统一换行
    normalized = _normalize(text)
    if not normalized:
        return []

    # 第二步：切段与逐级细分
    pieces: list[str] = []
    for para in normalized.split("\n\n"):
        para = para.strip()
        if not para:
            continue
        if len(para) <= chunk_size:
            pieces.append(para)
            continue
        for sub in para.split("\n"):
            sub = sub.strip()
            if not sub:
                continue
            if len(sub) <= chunk_size:
                pieces.append(sub)
                continue
            for sentence in _split_sentences(sub):
                if len(sentence) <= chunk_size:
                    pieces.append(sentence)
                else:
                    pieces.extend(_hard_split(sentence, chunk_size, overlap))

    # 第三步：贪心合并相邻小段
    chunks: list[str] = []
    buf = ""
    for piece in pieces:
        if not buf:
            buf = piece
        elif len(buf) + 1 + len(piece) <= chunk_size:
            buf = f"{buf}\n{piece}"
        else:
            chunks.append(buf)
            buf = piece
    if buf:
        chunks.append(buf)

    # 第四步：丢弃全空白块
    return [c for c in chunks if c.strip()]
