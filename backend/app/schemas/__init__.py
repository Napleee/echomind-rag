"""Pydantic 模型：API 请求 / 响应契约。前端类型定义必须与本文件对齐。"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class DocumentOut(BaseModel):
    id: int
    title: str
    source_type: str
    status: str
    chunk_count: int
    error: Optional[str] = None
    created_at: datetime


class DocumentStatusOut(BaseModel):
    id: int
    status: str
    chunk_count: int
    error: Optional[str] = None


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    conversation_id: Optional[int] = None
    top_k: Optional[int] = Field(default=None, ge=1, le=20)


class SourceOut(BaseModel):
    chunk_id: int
    document_id: int
    document_title: str
    seq: int
    score: float
    snippet: str


class ConversationOut(BaseModel):
    id: int
    title: Optional[str] = None
    created_at: datetime


class MessageOut(BaseModel):
    id: int
    role: str
    content: str
    sources: Optional[list[SourceOut]] = None
    created_at: datetime


__all__ = [
    "DocumentOut",
    "DocumentStatusOut",
    "ChatRequest",
    "SourceOut",
    "ConversationOut",
    "MessageOut",
]
