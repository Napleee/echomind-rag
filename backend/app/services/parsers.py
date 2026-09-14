"""文档解析服务：把 pdf / docx / md / txt / 会议 JSON 统一提取为纯文本。"""
import json
import logging
import pathlib

logger = logging.getLogger(__name__)


def _parse_pdf(path: pathlib.Path) -> str:
    """用 PyMuPDF 逐页提取文本，页之间用两个换行符连接。"""
    import fitz  # PyMuPDF

    pages: list[str] = []
    with fitz.open(str(path)) as doc:
        for page in doc:
            pages.append(page.get_text("text"))
    return "\n\n".join(pages)


def _parse_docx(path: pathlib.Path) -> str:
    """用 python-docx 提取全部段落文本，段落间换行符连接。"""
    import docx  # python-docx

    document = docx.Document(str(path))
    return "\n".join(p.text for p in document.paragraphs)


def _format_timestamp(value: object) -> str:
    """把秒数或 hh:mm:ss / mm:ss 字符串渲染为「[分:秒]」，解析失败返回空串。"""
    if isinstance(value, bool) or value is None:
        return ""
    total: int
    if isinstance(value, (int, float)):
        total = max(0, int(value))
    elif isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return ""
        parts = stripped.split(":")
        try:
            nums = [int(p) for p in parts]
        except ValueError:
            return ""
        total = 0
        for n in nums:
            total = total * 60 + n
    else:
        return ""
    return f"[{total // 60:d}:{total % 60:02d}]"


def _parse_meeting_json(path: pathlib.Path) -> str:
    """容错解析会议转写 JSON（yinyue-meeting 导出格式）。

    支持结构：顶层 dict 带 segments / utterances / transcript 任一列表字段，
    或顶层本身是列表；每项取 text 字段渲染为「[分:秒] 说话人: 文本」。
    完全不匹配时回退为全文 JSON 序列化返回。
    """
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError, OSError):
        logger.warning("会议 JSON 解析失败，按普通文本读取: %s", path)
        return path.read_text(encoding="utf-8", errors="replace")

    items: list[object] = []
    if isinstance(obj, list):
        items = obj
    elif isinstance(obj, dict):
        for key in ("segments", "utterances", "transcript"):
            value = obj.get(key)
            if isinstance(value, list):
                items = value
                break

    lines: list[str] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        text = item.get("text")
        if text is None or not str(text).strip():
            continue  # 无 text 的项跳过
        text = str(text).strip()

        start_raw = item.get("start") if item.get("start") is not None else item.get("start_time")
        ts = _format_timestamp(start_raw)
        speaker_raw = item.get("speaker")
        speaker = str(speaker_raw).strip() if speaker_raw else ""

        if ts and speaker:
            lines.append(f"{ts} {speaker}: {text}")
        elif ts:
            lines.append(f"{ts} {text}")
        elif speaker:
            lines.append(f"{speaker}: {text}")
        else:
            lines.append(text)

    if not lines:
        # 完全不匹配：全文序列化兜底
        return json.dumps(obj, ensure_ascii=False, indent=2)
    return "\n".join(lines)


def parse_file(path: pathlib.Path, source_type: str) -> str:
    """按 source_type 分发到对应解析器，返回纯文本。未知类型抛 ValueError。"""
    if source_type == "pdf":
        return _parse_pdf(path)
    if source_type == "docx":
        return _parse_docx(path)
    if source_type in ("md", "txt"):
        return path.read_text(encoding="utf-8", errors="replace")
    if source_type == "meeting_json":
        return _parse_meeting_json(path)
    raise ValueError(f"不支持的文档类型: {source_type}")
