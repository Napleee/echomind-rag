"""EchoMind 后端入口。"""
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api import chat, documents
from app.core.config import get_settings
from app.core.db import engine, init_db

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)
logger = logging.getLogger("echomind")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
    init_db()
    logger.info("数据库初始化完成")
    yield


app = FastAPI(title="EchoMind API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    """健康检查：顺带探测数据库连通性与 LLM 配置状态。"""
    s = get_settings()
    db_ok = False
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db_ok = True
    except Exception:  # noqa: BLE001 健康检查不抛错
        pass
    return {
        "status": "ok",
        "database": db_ok,
        "llm_configured": bool(s.llm_api_key),
        "embedding_model": s.embedding_model,
    }


app.include_router(documents.router)
app.include_router(chat.router)
