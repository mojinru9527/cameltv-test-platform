"""Environment & Variable Pydantic schemas."""
from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field


# ── Environment ──

class EnvironmentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    env_type: str = Field(default="test", pattern=r"^(dev|test|staging|prod)$")
    base_url: str = Field(default="", max_length=500)
    description: str = Field(default="", max_length=500)


class EnvironmentUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=120)
    env_type: str | None = Field(default=None, pattern=r"^(dev|test|staging|prod)$")
    base_url: str | None = Field(default=None, max_length=500)
    description: str | None = Field(default=None, max_length=500)


class EnvironmentResponse(BaseModel):
    id: int
    project_id: int
    name: str
    env_type: str
    base_url: str
    description: str
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


# ── Variable ──

class VariableCreate(BaseModel):
    key: str = Field(..., min_length=1, max_length=120)
    value: str = Field(default="")
    encrypted: bool = Field(default=False)
    description: str = Field(default="", max_length=500)


class VariableUpdate(BaseModel):
    key: str | None = Field(default=None, max_length=120)
    value: str | None = None
    encrypted: bool | None = None
    description: str | None = Field(default=None, max_length=500)


class VariableResponse(BaseModel):
    id: int
    environment_id: int
    key: str
    value: str
    encrypted: bool
    description: str
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


# ── Resolve ──

class VariableResolveRequest(BaseModel):
    template: str = Field(..., description="String containing ${VAR_NAME} references")
    environment_id: int


class VariableResolveResponse(BaseModel):
    resolved: str
