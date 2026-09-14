"""应用配置：统一从环境变量 / .env 读取（pydantic-settings）。"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # ---- LLM（OpenAI 兼容协议，换厂商只改这三个值）----
    llm_base_url: str = "https://api.deepseek.com"
    llm_api_key: str = ""  # 留空则进入 mock 模式：不调 LLM，直接回显检索结果
    llm_model: str = "deepseek-chat"

    # ---- Embedding（本地运行，免费）----
    embedding_model: str = "BAAI/bge-small-zh-v1.5"
    hf_endpoint: str = "https://hf-mirror.com"  # 国内镜像，避免 HuggingFace 直连失败

    # ---- 切块 ----
    chunk_size: int = 500       # 目标块大小（字符）
    chunk_overlap: int = 50     # 硬切长段时相邻块的重叠（字符）

    # ---- 检索 ----
    vector_top_k: int = 20      # 向量召回条数
    bm25_top_k: int = 20        # BM25 召回条数
    final_top_k: int = 5        # RRF 融合后送入 prompt 的条数
    rrf_k: int = 60             # RRF 融合常数
    enable_rerank: bool = False # 阶段3开启
    rerank_model: str = "BAAI/bge-reranker-base"

    # ---- 基础设施 ----
    database_url: str = "postgresql+psycopg://echomind:echomind@localhost:5432/echomind"
    redis_url: str = "redis://localhost:6379/0"

    # ---- 应用 ----
    upload_dir: str = "data/uploads"
    max_upload_mb: int = 20
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
