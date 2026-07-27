"""Dataset schemas."""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field


class DatasetCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str = ""
    source_type: str = Field(default="csv", pattern=r"^(csv|json)$")
    raw_content: str = Field(default="")


class DatasetUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=200)
    description: Optional[str] = None
    raw_content: Optional[str] = None


class DatasetOut(BaseModel):
    id: int
    project_id: int
    name: str
    description: str
    source_type: str
    raw_content: str
    sql_query: str
    connection_string: str
    row_count: int
    columns_meta: str
    created_at: str | None
    updated_at: str | None
    model_config = {"from_attributes": True}


class DatasetListItem(BaseModel):
    """Lighter version for list view — excludes raw_content."""
    id: int
    project_id: int
    name: str
    description: str
    source_type: str
    row_count: int
    columns_meta: str
    created_at: str | None
    updated_at: str | None
    model_config = {"from_attributes": True}


class DatasetPreview(BaseModel):
    """Preview of parsed dataset rows."""
    columns: list[str] = []
    rows: list[dict[str, str]] = []
    total_rows: int = 0


class DatasetUploadResponse(BaseModel):
    """Result after uploading/creating a dataset."""
    dataset: DatasetOut
    preview: DatasetPreview
