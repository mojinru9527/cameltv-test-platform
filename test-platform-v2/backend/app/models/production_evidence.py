"""AITDE V3.6 — Production Evidence & Real-World Data Template 数据模型。

只读、可审计、脱敏地把生产真实行为与数据拓扑引入 Evidence Plane。所有枚举
列使用 String 值以在 SQLite / PostgreSQL 上稳定；JSON 结构以 Text 存储。
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class ProductionObservationSession(Base):
    """一次生产观察会话（OBSERVE | READONLY_EXPLORE）。"""

    __tablename__ = "production_observation_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(Integer, default=0, index=True)
    mission_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    environment_id: Mapped[int] = mapped_column(Integer, default=0, index=True)
    worker_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    mode: Mapped[str] = mapped_column(String(32), default="OBSERVE", index=True)
    status: Mapped[str] = mapped_column(String(16), default="ACTIVE", index=True)
    policy_version: Mapped[str] = mapped_column(String(32), default="1.0")
    started_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    started_at: Mapped[datetime] = mapped_column(default=datetime.now, index=True)
    finished_at: Mapped[datetime | None] = mapped_column(nullable=True)


class ObservedJourney(Base):
    """一次观察会话归纳出的用户真实 Journey（行为路径）。"""

    __tablename__ = "observed_journeys"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(Integer, default=0, index=True)
    mission_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    session_id: Mapped[int] = mapped_column(Integer, default=0, index=True)
    name: Mapped[str] = mapped_column(String(128), default="")
    journey_hash: Mapped[str] = mapped_column(String(64), default="", index=True)
    summary_json: Mapped[str] = mapped_column(Text, default="{}")
    source_ref_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(default=datetime.now, index=True)


class ObservedJourneyStep(Base):
    """Journey 内的单步事件（navigation / xhr / semantic action）。"""

    __tablename__ = "observed_journey_steps"

    id: Mapped[int] = mapped_column(primary_key=True)
    journey_id: Mapped[int] = mapped_column(Integer, default=0, index=True)
    sequence: Mapped[int] = mapped_column(Integer, default=0)
    event_type: Mapped[str] = mapped_column(String(32), default="NAVIGATE")
    semantic_action_json: Mapped[str] = mapped_column(Text, default="{}")
    url_template: Mapped[str] = mapped_column(String(512), default="")
    xhr_refs_json: Mapped[str] = mapped_column(Text, default="[]")
    evidence_refs_json: Mapped[str] = mapped_column(Text, default="[]")
    timestamp: Mapped[datetime] = mapped_column(default=datetime.now, index=True)


class ProductionQueryAudit(Base):
    """针对生产数据源的每次查询审计（100% 覆盖）。"""

    __tablename__ = "production_query_audits"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(Integer, default=0, index=True)
    session_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    data_source_id: Mapped[int] = mapped_column(Integer, default=0, index=True)
    query_fingerprint: Mapped[str] = mapped_column(String(64), default="", index=True)
    operation_type: Mapped[str] = mapped_column(String(16), default="SELECT", index=True)
    schema_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    table_names_json: Mapped[str] = mapped_column(Text, default="[]")
    row_count: Mapped[int] = mapped_column(Integer, default=0)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    policy_decision: Mapped[str] = mapped_column(String(16), default="ALLOW", index=True)
    executed_at: Mapped[datetime] = mapped_column(default=datetime.now, index=True)


class MaskingProfile(Base):
    """脱敏 Profile（一组 MaskingRule）。"""

    __tablename__ = "masking_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(Integer, default=0, index=True)
    name: Mapped[str] = mapped_column(String(128), default="")
    version: Mapped[str] = mapped_column(String(32), default="1.0")
    status: Mapped[str] = mapped_column(String(16), default="ACTIVE", index=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.now, index=True)


class MaskingRule(Base):
    """单条脱敏规则：字段匹配 → 分类 → 策略。"""

    __tablename__ = "masking_rules"

    id: Mapped[int] = mapped_column(primary_key=True)
    profile_id: Mapped[int] = mapped_column(Integer, default=0, index=True)
    entity_pattern: Mapped[str] = mapped_column(String(128), default="*")
    field_pattern: Mapped[str] = mapped_column(String(128), default="*", index=True)
    classification: Mapped[str] = mapped_column(String(32), default="PII")
    strategy: Mapped[str] = mapped_column(
        String(16), default="HASH", index=True
    )  # REDACT|HASH|TOKENIZE|FAKE|PRESERVE
    config_json: Mapped[str] = mapped_column(Text, default="{}")
    priority: Mapped[int] = mapped_column(Integer, default=0, index=True)


class EntityGraphSnapshot(Base):
    """以业务根实体为入口抽取的关联拓扑快照（脱敏前）。"""

    __tablename__ = "entity_graph_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(Integer, default=0, index=True)
    mission_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    source_environment_id: Mapped[int] = mapped_column(Integer, default=0, index=True)
    root_entity_type: Mapped[str] = mapped_column(String(64), default="", index=True)
    root_ref_hash: Mapped[str] = mapped_column(String(64), default="", index=True)
    graph_json: Mapped[str] = mapped_column(Text, default="{}")
    content_hash: Mapped[str] = mapped_column(String(64), default="", index=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.now, index=True)


class ProdDataTemplate(Base):
    """脱敏后 Graph → 可测试模板。"""

    __tablename__ = "prod_data_templates"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(Integer, default=0, index=True)
    mission_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(128), default="")
    entity_graph_snapshot_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    masking_profile_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    template_json: Mapped[str] = mapped_column(Text, default="{}")
    validation_status: Mapped[str] = mapped_column(
        String(16), default="PENDING", index=True
    )  # PENDING|VALID|INVALID
    created_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.now, index=True)


class TemplateMaterialization(Base):
    """模板 → Test Environment 物化记录（V3.2 Fixture 集成）。"""

    __tablename__ = "template_materializations"

    id: Mapped[int] = mapped_column(primary_key=True)
    template_id: Mapped[int] = mapped_column(Integer, default=0, index=True)
    target_environment_id: Mapped[int] = mapped_column(Integer, default=0, index=True)
    fixture_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(16), default="PENDING", index=True)
    id_remap_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(default=datetime.now, index=True)
