"""ReleaseBundle — aggregates one release's client + admin versions + attachments.

A "release" is the union of:
  - client-side .rp (用户端: APP + PC + WEB)
  - admin-side .rp  (运营后台)
  - optional attachments (说明附件)

Each bundle links to its parent via parent_bundle_id, forming a version chain
for incremental diff and evolution tracking across releases.
"""
from __future__ import annotations

from datetime import date

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.base import TimestampMixin


class ReleaseBundle(Base, TimestampMixin):
    """A complete release package aggregating one version's worth of requirements.

    Fields by version:
      v1.0 (10): id, project_id, name, description, client_version, admin_version,
                 status, release_date, created_at, updated_at
      v1.1 (+2): parent_bundle_id, diff_summary
      v1.3 (+1): global_navigation
      ── Total: 13 ──
    """
    __tablename__ = "release_bundle"

    # ── v1.0 base ──
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(default=0, index=True)

    name: Mapped[str] = mapped_column(String(500), default="")
    description: Mapped[str] = mapped_column(Text, default="")

    client_version: Mapped[str] = mapped_column(
        String(100), default="", index=True
    )  # e.g. "14.1.0" — from 用户端 蓝湖更新日志
    admin_version: Mapped[str] = mapped_column(
        String(100), default="", index=True
    )  # e.g. "8.2.0" — from 运营后台 蓝湖更新日志 (independent versioning)

    status: Mapped[str] = mapped_column(
        String(30), default="draft", index=True
    )  # draft | active | archived

    release_date: Mapped[date | None] = mapped_column(default=None)

    # ── v1.1: version chain + diff ──
    parent_bundle_id: Mapped[int | None] = mapped_column(
        ForeignKey("release_bundle.id", ondelete="SET NULL"),
        default=None, index=True,
    )  # previous version bundle, forming release chain (v1 → v2 → v3)
    diff_summary: Mapped[str] = mapped_column(
        Text, default="{}"
    )  # JSON: structured diff vs parent (module counts, change breakdown)

    # ── v1.3: global navigation ──
    global_navigation: Mapped[str] = mapped_column(
        Text, default="[]"
    )  # JSON array of global navigation items (>80% page occurrence threshold)
    # Schema: [{
    #   "trigger": "底部导航-首页", "target_page": "首页",
    #   "interaction_type": "global_navigation",
    #   "coverage": 1.0  # fraction of pages containing this interaction
    # }]
