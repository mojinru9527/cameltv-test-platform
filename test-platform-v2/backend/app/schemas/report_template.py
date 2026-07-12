"""ReportTemplate Pydantic schemas — R4a report template feature."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class SectionDef(BaseModel):
    """A single section definition within a report template."""
    key: str = ""
    label: str = ""
    enabled: bool = True
    order: int = 0


class TemplateCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str = ""
    sections: list[SectionDef] = Field(default_factory=list)
    is_default: bool = False


class TemplateUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = None
    sections: list[SectionDef] | None = None
    is_default: bool | None = None


class TemplateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int = 0
    name: str = ""
    description: str = ""
    sections: list[SectionDef] = Field(default_factory=list)
    is_default: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
