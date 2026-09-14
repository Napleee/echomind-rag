"""检索质量评估脚本：对 questions.yaml 中的问题执行检索，计算 recall@k。

用法（在 backend/ 目录下）:
    python -m eval.run_eval             # 默认 k=5，全部题目
    python -m eval.run_eval --k 10      # 评估 recall@10
    python -m eval.run_eval --limit 3   # 只跑前 3 题

说明: 本脚本为命令行评估工具，print 输出即为最终报告，便于重定向存档。
"""
import argparse
import sys
from pathlib import Path

# 保证从任意工作目录运行都能 import 到 app 包
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

QUESTIONS_FILE = Path(__file__).resolve().parent / "questions.yaml"


def _strip_quotes(s: str) -> str:
    """去掉 YAML 值两侧的成对引号。"""
    s = s.strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in ("\"", "'"):
        return s[1:-1]
    return s


def _parse_simple_yaml(text: str) -> list[dict]:
    """极简 YAML 解析兜底：仅支持 questions.yaml 的固定结构（PyYAML 缺失时使用）。"""
    items: list[dict] = []
    current: dict | None = None
    in_keywords = False
    for raw in text.splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("- question:"):
            current = {
                "question": _strip_quotes(stripped.split(":", 1)[1]),
                "expected_keywords": [],
            }
            items.append(current)
            in_keywords = False
        elif stripped == "expected_keywords:":
            in_keywords = True
        elif stripped.startswith("- ") and in_keywords and current is not None:
            current["expected_keywords"].append(_strip_quotes(stripped[2:]))
    return items


def load_questions(path: Path) -> list[dict]:
    """加载评估问题集，返回 [{question, expected_keywords}, ...]。"""
    text = path.read_text(encoding="utf-8")
    try:
        import yaml  # PyYAML 随 sentence-transformers 传递安装
    except ImportError:
        return _parse_simple_yaml(text)
    data = yaml.safe_load(text)
    items = data.get("questions", []) if isinstance(data, dict) else data
    return [
        {
            "question": str(item["question"]),
            "expected_keywords": [str(k) for k in item.get("expected_keywords", [])],
        }
        for item in items
    ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="EchoMind 检索质量评估：计算 recall@k")
    parser.add_argument("--k", type=int, default=5, help="每题参与判定的检索条数（默认 5）")
    parser.add_argument("--limit", type=int, default=None, help="只评估前 N 道题（默认全部）")
    return parser.parse_args()


def _preflight() -> None:
    """预检：数据库可达且知识库非空，否则给出友好提示后退出。"""
    from sqlalchemy import text

    from app.core.db import SessionLocal, engine
    from app.models import Chunk

    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001 预检失败统一转成友好提示
        print(f"[错误] 无法连接数据库: {exc}")
        print("请先在项目根目录执行 `docker compose up -d` 启动 PostgreSQL，")
        print("并确认 .env 中 DATABASE_URL 与 docker-compose.yml 的端口一致。")
        sys.exit(1)

    try:
        with SessionLocal() as db:
            chunk_count = db.query(Chunk).count()
    except Exception as exc:  # noqa: BLE001
        print(f"[错误] 读取知识库失败: {exc}")
        sys.exit(1)
    if chunk_count == 0:
        print("[提示] 知识库为空: 请先启动后端并上传文档（可用 samples/ 目录语料），再运行评估。")
        sys.exit(1)


def main() -> None:
    args = parse_args()

    questions = load_questions(QUESTIONS_FILE)
    if not questions:
        print(f"[错误] 问题集为空: {QUESTIONS_FILE}")
        sys.exit(1)
    if args.limit is not None:
        questions = questions[: args.limit]

    _preflight()

    # 延迟导入重依赖：保证 --help / 预检失败时不加载模型
    from app.services import retriever
    from app.services.embedder import get_embedder

    try:
        embedder = get_embedder()
    except Exception as exc:  # noqa: BLE001
        print(f"[错误] 加载 Embedding 模型失败: {exc}")
        print("提示: 首次运行需下载模型，国内网络请确认 .env 中 HF_ENDPOINT=https://hf-mirror.com")
        sys.exit(1)

    print(f"共 {len(questions)} 道题，评估 recall@{args.k}")
    print("-" * 60)

    hits = 0
    for idx, item in enumerate(questions, 1):
        question: str = item["question"]
        keywords: list[str] = item["expected_keywords"]
        query_embedding = embedder.embed_query(question)
        try:
            chunks = retriever.search(question, query_embedding)[: args.k]
        except Exception as exc:  # noqa: BLE001
            print(f"[错误] 检索失败: {exc}")
            print("提示: 请确认数据库已启动（docker compose up -d）且 pgvector 扩展可用。")
            sys.exit(1)

        blob = "\n".join(chunk.content for chunk in chunks)
        matched = [kw for kw in keywords if kw in blob]
        ok = bool(matched)
        hits += int(ok)
        print(f"[{'PASS' if ok else 'FAIL'}] {idx}. {question}")
        print(f"       命中关键词: {'、'.join(matched) if matched else '无'}（参与判定 {len(chunks)} 块）")

    print("-" * 60)
    recall = hits / len(questions)
    print(f"recall@{args.k}: {hits}/{len(questions)} = {recall:.2%}")


if __name__ == "__main__":
    main()
