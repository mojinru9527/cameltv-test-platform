"""Dataset API — /api/v1/datasets/*"""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import CurrentUser, require_permission
from app.schemas.common import Page, R
from app.schemas.dataset import (
    DatasetCreate, DatasetListItem, DatasetOut, DatasetPreview,
    DatasetUpdate, DatasetUploadResponse,
)
from app.services import dataset_service

router = APIRouter(prefix="/datasets", tags=["测试数据集"])


# ── List ──
@router.get("", response_model=R[Page[DatasetListItem]])
def list_datasets(
    page: int = 1,
    page_size: int = 20,
    current: CurrentUser = Depends(require_permission("dataset:list")),
    db: Session = Depends(get_db),
):
    items, total = dataset_service.list_datasets(
        db, project_id=current.project_id or 0, page=page, page_size=page_size,
    )
    return R.ok(Page(
        total=total, page=page, page_size=page_size,
        items=[DatasetListItem(**it) for it in items],
    ))


# ── Get detail ──
@router.get("/{dataset_id}", response_model=R[DatasetOut])
def get_dataset(
    dataset_id: int,
    current: CurrentUser = Depends(require_permission("dataset:list")),
    db: Session = Depends(get_db),
):
    row = dataset_service.get_dataset(db, dataset_id, project_id=current.project_id or 0)
    if not row:
        return R(code=404, msg="数据集不存在")
    return R.ok(DatasetOut(**row))


# ── Create (paste content) ──
@router.post("", response_model=R[DatasetUploadResponse])
def create_dataset(
    body: DatasetCreate,
    current: CurrentUser = Depends(require_permission("dataset:create")),
    db: Session = Depends(get_db),
):
    try:
        row = dataset_service.create_dataset(db, current.project_id or 0, body.model_dump())
        preview = dataset_service.preview_dataset(body.raw_content, body.source_type)
        return R.ok(DatasetUploadResponse(
            dataset=DatasetOut(**row),
            preview=DatasetPreview(**preview),
        ))
    except (ValueError, Exception) as e:
        return R(code=1, msg=str(e))


# ── Update ──
@router.put("/{dataset_id}", response_model=R[DatasetOut])
def update_dataset(
    dataset_id: int,
    body: DatasetUpdate,
    current: CurrentUser = Depends(require_permission("dataset:update")),
    db: Session = Depends(get_db),
):
    row = dataset_service.update_dataset(db, dataset_id, body.model_dump(exclude_none=True))
    if not row:
        return R(code=404, msg="数据集不存在")
    return R.ok(DatasetOut(**row))


# ── Delete ──
@router.delete("/{dataset_id}", response_model=R[dict])
def delete_dataset(
    dataset_id: int,
    current: CurrentUser = Depends(require_permission("dataset:delete")),
    db: Session = Depends(get_db),
):
    ok = dataset_service.delete_dataset(db, dataset_id, project_id=current.project_id or 0)
    if not ok:
        return R(code=404, msg="数据集不存在或无权操作")
    return R.ok({"deleted": dataset_id})


# ── Upload file (CSV/JSON) ──
@router.post("/upload", response_model=R[DatasetUploadResponse])
def upload_dataset(
    file: UploadFile = File(...),
    name: str = Form(..., description="数据集名称"),
    description: str = Form(""),
    req: Request = None,
    current: CurrentUser = Depends(require_permission("dataset:create")),
    db: Session = Depends(get_db),
):
    """Upload a CSV or JSON file as a new dataset."""
    if not file.filename:
        return R(code=1, msg="请上传文件")

    # P1-5a: Content-Length 前置检查，避免读取超大文件 (max 10 MB)
    if req:
        content_length = req.headers.get("content-length")
        if content_length:
            cl = int(content_length)
            max_bytes = 10 * 1024 * 1024
            if cl > max_bytes:
                return R(code=1, msg=f"文件大小超过 10MB 限制 (got {cl / (1024*1024):.1f} MB)")

    # Size check: 10 MB limit (二次校验)
    content_bytes = file.file.read()
    if len(content_bytes) > 10 * 1024 * 1024:
        return R(code=1, msg="文件大小超过 10MB 限制")

    try:
        raw_content = content_bytes.decode("utf-8-sig")
    except UnicodeDecodeError:
        return R(code=1, msg="文件编码不支持，请使用 UTF-8 编码")

    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext == "csv":
        source_type = "csv"
    elif ext == "json":
        source_type = "json"
    else:
        return R(code=1, msg="仅支持 .csv 或 .json 文件")

    try:
        row = dataset_service.create_dataset(db, current.project_id or 0, {
            "name": name, "description": description,
            "source_type": source_type, "raw_content": raw_content,
        })
        preview = dataset_service.preview_dataset(raw_content, source_type)
        return R.ok(DatasetUploadResponse(
            dataset=DatasetOut(**row),
            preview=DatasetPreview(**preview),
        ))
    except ValueError as e:
        return R(code=1, msg=str(e))


# ── Preview (without saving) ──
class PreviewRequest(BaseModel):
    source_type: str = "csv"
    raw_content: str


@router.post("/preview", response_model=R[DatasetPreview])
def preview_dataset(
    body: PreviewRequest,
    current: CurrentUser = Depends(require_permission("dataset:create")),
):
    """Preview parsed rows from raw content without saving to the database."""
    try:
        preview = dataset_service.preview_dataset(body.raw_content, body.source_type)
        return R.ok(DatasetPreview(**preview))
    except (ValueError, Exception) as e:
        return R(code=1, msg=str(e))
