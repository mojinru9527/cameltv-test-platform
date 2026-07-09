"""Version mission models for release-level QA orchestration."""
from __future__ import annotations

from sqlalchemy import Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.base import TimestampMixin


class VersionMission(Base, TimestampMixin):
    __tablename__ = "version_mission"
    __table_args__ = (UniqueConstraint("project_id", "mission_key", name="uq_version_mission_key"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(default=0, index=True)
    mission_key: Mapped[str] = mapped_column(default="", index=True)
    title: Mapped[str] = mapped_column(default="")
    version: Mapped[str] = mapped_column(default="", index=True)
    requirement_url: Mapped[str] = mapped_column(Text, default="")
    test_env_url: Mapped[str] = mapped_column(Text, default="")
    admin_env_url: Mapped[str] = mapped_column(Text, default="")
    environment_id: Mapped[int | None] = mapped_column(default=None, index=True)
    requirement_doc_id: Mapped[int | None] = mapped_column(default=None, index=True)
    test_plan_id: Mapped[int | None] = mapped_column(default=None, index=True)
    status: Mapped[str] = mapped_column(default="draft", index=True)
    scope: Mapped[str] = mapped_column(Text, default="{}")
    summary: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[int] = mapped_column(default=0, index=True)
    qa_owner_id: Mapped[int] = mapped_column(default=0, index=True)


class AgentWorkLog(Base, TimestampMixin):
    __tablename__ = "agent_work_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(default=0, index=True)
    mission_id: Mapped[int] = mapped_column(index=True)
    department: Mapped[str] = mapped_column(default="", index=True)
    agent_name: Mapped[str] = mapped_column(default="")
    action: Mapped[str] = mapped_column(default="", index=True)
    status: Mapped[str] = mapped_column(default="done", index=True)
    input_ref: Mapped[str] = mapped_column(Text, default="")
    output_ref: Mapped[str] = mapped_column(Text, default="")
    detail: Mapped[str] = mapped_column(Text, default="")
    payload: Mapped[str] = mapped_column(Text, default="{}")
    duration_ms: Mapped[int] = mapped_column(default=0)


class GeneratedArtifact(Base, TimestampMixin):
    __tablename__ = "generated_artifact"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(default=0, index=True)
    mission_id: Mapped[int] = mapped_column(index=True)
    artifact_type: Mapped[str] = mapped_column(default="", index=True)
    source: Mapped[str] = mapped_column(default="", index=True)
    name: Mapped[str] = mapped_column(default="")
    ref_id: Mapped[str] = mapped_column(default="")
    content: Mapped[str] = mapped_column(Text, default="")
    meta: Mapped[str] = mapped_column(Text, default="{}")
