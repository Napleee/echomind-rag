"""SQLAlchemy 模型：EchoMind 全部数据表。"""
from datetime import datetime
from typing import Optional, Union

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pgvector.sqlalchemy import Vector

from app.core.db import Base

EMBEDDING_DIM = 512  # bge-small-zh-v1.5 输出维度


class Document(Base):
    """上传的原始文档。"""

    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(512))
    source_type: Mapped[str] = mapped_column(String(32))  # pdf / docx / md / txt / meeting_json
    file_path: Mapped[str] = mapped_column(String(1024), default="")
    # 状态机: processing → ready / error
    status: Mapped[str] = mapped_column(String(16), default="processing", index=True)
    error: Mapped[Optional[str]] = mapped_column(Text, default=None, nullable=True)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    chunks: Mapped[list["Chunk"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )


class Chunk(Base):
    """切块 + 向量，检索的基本单位。"""

    __tablename__ = "chunks"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    seq: Mapped[int] = mapped_column(Integer)  # 在文档内的顺序号
    content: Mapped[str] = mapped_column(Text)
    embedding: Mapped[Optional[list[float]]] = mapped_column(
        Vector(EMBEDDING_DIM), default=None, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    document: Mapped["Document"] = relationship(back_populates="chunks")

    __table_args__ = (
        Index("chunks_doc_seq_idx", "document_id", "seq"),
        # HNSW 向量索引（余弦距离）；百万级以下规模足够，参数可再调
        Index(
            "chunks_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )


class Conversation(Base):
    """一轮对话会话。"""

    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[Optional[str]] = mapped_column(String(256), default=None, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Message(Base):
    """对话消息。sources 记录回答引用的片段，用于前端溯源展示。"""

    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[str] = mapped_column(String(16))  # user / assistant
    content: Mapped[str] = mapped_column(Text)
    sources: Mapped[Optional[Union[dict, list]]] = mapped_column(JSONB, default=None, nullable=True)
    latency_ms: Mapped[Optional[int]] = mapped_column(Integer, default=None, nullable=True)
    prompt_tokens: Mapped[Optional[int]] = mapped_column(Integer, default=None, nullable=True)
    completion_tokens: Mapped[Optional[int]] = mapped_column(Integer, default=None, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


__all__ = ["Document", "Chunk", "Conversation", "Message", "EMBEDDING_DIM"]
