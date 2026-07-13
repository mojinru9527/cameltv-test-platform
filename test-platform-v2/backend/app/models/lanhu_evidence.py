"""蓝湖证据包模型 —— 证据链事实层。

对应《Lanhu Evidence Pack OCR Implementation Plan》§3。四张表：
  - lanhu_evidence_job：一次导入/采集任务（页面树发现→截图→OCR→合并→导出→导入）。
  - lanhu_evidence_page：页面树中的一个蓝湖页面，含 DOM/OCR/合并文本与质量。
  - lanhu_evidence_asset：截图 / Word / JSON / 文件资产（可追溯到具体页面）。
  - lanhu_ocr_block：每张截图的 OCR 输出块（文本 + 置信度 + bbox）。

设计沿用知识中心/Wiki 约定：project_id 松散作用域（无 FK）、枚举以 str + 注释、
JSON 存 Text。证据为不可变事实层，LLM 摘要发生在后续步骤且不得覆盖证据。
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.base import TimestampMixin


class LanhuEvidenceJob(Base, TimestampMixin):
    """一次证据包采集任务。"""
    __tablename__ = "lanhu_evidence_job"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(index=True)
    source_url: Mapped[str] = mapped_column(Text, default="")
    doc_id: Mapped[str] = mapped_column(default="", index=True)
    version_id: Mapped[str] = mapped_column(default="", index=True)
    root_page_id: Mapped[str] = mapped_column(default="", index=True)
    document_name: Mapped[str] = mapped_column(default="")
    # pending/running/success/success_with_warnings/failed/cancelled
    status: Mapped[str] = mapped_column(default="pending", index=True)
    # queued/discovering/capturing/ocr/merging/exporting/importing/done
    stage: Mapped[str] = mapped_column(default="queued")
    total_pages: Mapped[int] = mapped_column(default=0)
    captured_pages: Mapped[int] = mapped_column(default=0)
    ocr_pages: Mapped[int] = mapped_column(default=0)
    failed_pages: Mapped[int] = mapped_column(default=0)
    word_path: Mapped[str] = mapped_column(default="")
    json_path: Mapped[str] = mapped_column(default="")
    storage_dir: Mapped[str] = mapped_column(default="")
    quality_json: Mapped[str] = mapped_column(Text, default="{}")
    error_message: Mapped[str] = mapped_column(Text, default="")
    cancel_requested: Mapped[bool] = mapped_column(default=False)
    creator_id: Mapped[int] = mapped_column(default=0)
    started_at: Mapped[datetime | None] = mapped_column(default=None)
    finished_at: Mapped[datetime | None] = mapped_column(default=None)


class LanhuEvidencePage(Base, TimestampMixin):
    """页面树中的一个蓝湖页面。"""
    __tablename__ = "lanhu_evidence_page"

    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(index=True)
    project_id: Mapped[int] = mapped_column(index=True)
    page_id: Mapped[str] = mapped_column(default="", index=True)
    page_name: Mapped[str] = mapped_column(default="")
    page_path: Mapped[str] = mapped_column(default="")
    folder: Mapped[str] = mapped_column(default="")
    order_index: Mapped[int] = mapped_column(default=0)
    page_url: Mapped[str] = mapped_column(Text, default="")
    local_url: Mapped[str] = mapped_column(Text, default="")
    # pending/success/failed/skipped
    capture_status: Mapped[str] = mapped_column(default="pending", index=True)
    # pending/success/unavailable/failed
    ocr_status: Mapped[str] = mapped_column(default="pending", index=True)
    dom_text: Mapped[str] = mapped_column(Text, default="")
    ocr_text: Mapped[str] = mapped_column(Text, default="")
    merged_text: Mapped[str] = mapped_column(Text, default="")
    segment_count: Mapped[int] = mapped_column(default=0)
    quality_json: Mapped[str] = mapped_column(Text, default="{}")
    error_message: Mapped[str] = mapped_column(Text, default="")


class LanhuEvidenceAsset(Base, TimestampMixin):
    """截图 / Word / JSON / 文件资产。"""
    __tablename__ = "lanhu_evidence_asset"

    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(index=True)
    page_id: Mapped[int | None] = mapped_column(default=None, index=True)
    project_id: Mapped[int] = mapped_column(index=True)
    # screenshot/word/json/other
    asset_type: Mapped[str] = mapped_column(default="", index=True)
    file_path: Mapped[str] = mapped_column(Text, default="")
    relative_path: Mapped[str] = mapped_column(Text, default="")
    mime_type: Mapped[str] = mapped_column(default="")
    width: Mapped[int] = mapped_column(default=0)
    height: Mapped[int] = mapped_column(default=0)
    scroll_top: Mapped[int] = mapped_column(default=0)
    viewport_height: Mapped[int] = mapped_column(default=0)
    sha256: Mapped[str] = mapped_column(default="", index=True)
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")


class LanhuOcrBlock(Base):
    """单张截图的 OCR 输出块。"""
    __tablename__ = "lanhu_ocr_block"

    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(index=True)
    page_id: Mapped[int] = mapped_column(index=True)
    asset_id: Mapped[int] = mapped_column(index=True)
    project_id: Mapped[int] = mapped_column(index=True)
    text: Mapped[str] = mapped_column(Text, default="")
    confidence: Mapped[float] = mapped_column(default=0.0)
    bbox_json: Mapped[str] = mapped_column(Text, default="[]")
    order_index: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)
