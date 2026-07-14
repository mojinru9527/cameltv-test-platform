"""蓝湖证据包 Pydantic schema —— 请求/响应 DTO。

对应《Lanhu Evidence Pack OCR Implementation Plan》§3 Step 5。请求/响应分离，
使用 ConfigDict(from_attributes=True) 支持从 ORM 对象直接构造。
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class LanhuEvidenceCreateRequest(BaseModel):
    url: str = Field(..., min_length=1)
    capture_all_pages: bool = True
    include_word: bool = True
    include_json: bool = True
    import_to_requirement: bool = False
    import_to_knowledge: bool = False
    import_to_wiki: bool = False


class LanhuEvidenceJobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    source_url: str
    doc_id: str = ""
    version_id: str = ""
    root_page_id: str = ""
    document_name: str = ""
    status: str
    stage: str
    total_pages: int = 0
    captured_pages: int = 0
    ocr_pages: int = 0
    failed_pages: int = 0
    quality_json: str = "{}"
    error_message: str = ""
    attempt_no: int = 1
    parent_job_id: int | None = None
    import_result_json: str = "{}"
    requested_options_json: str = "{}"
    heartbeat_at: datetime | None = None
    created_at: datetime | None = None
    finished_at: datetime | None = None


class LanhuEvidencePageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    job_id: int
    page_id: str = ""
    page_name: str = ""
    page_path: str = ""
    folder: str = ""
    order_index: int = 0
    capture_status: str = "pending"
    ocr_status: str = "pending"
    segment_count: int = 0
    dom_text: str = ""
    ocr_text: str = ""
    merged_text: str = ""
    quality_json: str = "{}"
    error_message: str = ""
    capture_truncated: bool = False
    review_status: str = "pending"
    review_comment: str = ""
    reviewed_at: datetime | None = None


class LanhuEvidenceAssetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    job_id: int
    page_id: int | None = None
    asset_type: str = ""
    relative_path: str = ""
    mime_type: str = ""
    width: int = 0
    height: int = 0
    scroll_top: int = 0
    viewport_height: int = 0
    sha256: str = ""


class LanhuEvidenceImportRequest(BaseModel):
    import_to_requirement: bool = False
    import_to_knowledge: bool = False
    import_to_wiki: bool = False


class LanhuEvidencePageReviewRequest(BaseModel):
    approved: bool
    comment: str = Field(..., min_length=3, max_length=1000)
