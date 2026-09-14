"""文档管理端点：上传 / 列表 / 状态 / 重建索引 / 删除。"""
import logging
import uuid
from pathlib import Path

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    HTTPException,
    Request,
    UploadFile,
)
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db import get_db
from app.models import Chunk, Document
from app.schemas import DocumentOut, DocumentStatusOut
from app.services import cache
from app.services.ingestion import run_ingestion

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/documents", tags=["documents"])

# 允许上传的扩展名白名单
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".md", ".txt", ".json"}


@router.post("", status_code=202, response_model=DocumentOut)
async def upload_document(
    background_tasks: BackgroundTasks,
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> DocumentOut:
    """上传文档：校验扩展名与大小后落盘，创建 Document 记录并后台触发入库管线。"""
    settings = get_settings()
    original_name = file.filename or "未命名"
    ext = Path(original_name).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"不支持的文件类型: {ext or '（无扩展名）'}")

    max_bytes = settings.max_upload_mb * 1024 * 1024

    # 先按 Content-Length 预检，超限直接拒绝，避免把超大请求体读入内存
    content_length = request.headers.get("content-length")
    if content_length is not None and content_length.isdigit() and int(content_length) > max_bytes:
        raise HTTPException(
            status_code=413, detail=f"文件超过大小限制 {settings.max_upload_mb}MB"
        )

    # 分块读取并累计字节数，一旦超限立即中止，而不是一次性 read 全量内容
    blocks: list[bytes] = []
    total = 0
    while True:
        block = await file.read(1024 * 1024)
        if not block:
            break
        total += len(block)
        if total > max_bytes:
            raise HTTPException(
                status_code=413, detail=f"文件超过大小限制 {settings.max_upload_mb}MB"
            )
        blocks.append(block)
    data = b"".join(blocks)

    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    path = upload_dir / f"{uuid.uuid4().hex}{ext}"  # uuid4 文件名，保留原扩展名
    path.write_bytes(data)

    # json 视为会议转写导出，其余取小写扩展名
    source_type = "meeting_json" if ext == ".json" else ext.lstrip(".")
    doc = Document(
        title=Path(original_name).stem[:512],
        source_type=source_type,
        file_path=str(path),
        status="processing",
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)  # 取回服务端生成的 id / created_at

    background_tasks.add_task(run_ingestion, doc.id, str(path), source_type)
    cache.invalidate_cache()  # 知识库变更，旧缓存失效
    return DocumentOut.model_validate(doc, from_attributes=True)


@router.get("", response_model=list[DocumentOut])
def list_documents(db: Session = Depends(get_db)) -> list[DocumentOut]:
    """文档列表，created_at 倒序。"""
    docs = db.scalars(
        select(Document).order_by(Document.created_at.desc(), Document.id.desc())
    ).all()
    return [DocumentOut.model_validate(d, from_attributes=True) for d in docs]


@router.get("/{document_id}/status", response_model=DocumentStatusOut)
def get_document_status(
    document_id: int, db: Session = Depends(get_db)
) -> DocumentStatusOut:
    """查询单个文档的入库状态（前端轮询用）。"""
    doc = db.get(Document, document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="文档不存在")
    return DocumentStatusOut.model_validate(doc, from_attributes=True)


@router.post("/{document_id}/reindex", status_code=202, response_model=DocumentOut)
def reindex_document(
    document_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> DocumentOut:
    """重建索引：删除旧 chunks，置为 processing 后重跑入库管线。"""
    doc = db.get(Document, document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="文档不存在")
    db.execute(delete(Chunk).where(Chunk.document_id == document_id))
    doc.status = "processing"
    doc.error = None
    doc.chunk_count = 0
    db.commit()
    db.refresh(doc)

    background_tasks.add_task(run_ingestion, doc.id, doc.file_path, doc.source_type)
    cache.invalidate_cache()  # 知识库变更，旧缓存失效
    return DocumentOut.model_validate(doc, from_attributes=True)


@router.delete("/{document_id}", status_code=204)
def delete_document(document_id: int, db: Session = Depends(get_db)) -> None:
    """删除文档（chunks 级联删除）。"""
    doc = db.get(Document, document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="文档不存在")
    db.delete(doc)
    db.commit()
    cache.invalidate_cache()  # 知识库变更，旧缓存失效
