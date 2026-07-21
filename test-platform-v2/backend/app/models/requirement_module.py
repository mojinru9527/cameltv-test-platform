"""RequirementModule — hierarchical module→page→function-point tree built from Lanhu imports.

Represents the "project sphere" knowledge graph backbone:
    ReleaseBundle → Platform(APP/PC/WEB/ADMIN) → Module → Page → FunctionPoint
"""
from __future__ import annotations

from sqlalchemy import Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.base import TimestampMixin


class RequirementModule(Base, TimestampMixin):
    """A node in the hierarchical module tree extracted from a Lanhu release.

    node_type hierarchy: module > page > function_point
    leaf nodes can also be: attachment (docx/pdf说明文件)

    Fields by version:
      v1.0 (10): id, project_id, release_bundle_id, name, node_type, platform,
                 lanhu_page_id, change_type, created_at, updated_at
      v1.1 (+4): parent_module_id, source_version, screenshot_urls, has_visual_only_content
      v1.2 (+1): page_interactions
      ── Total: 15 ──
    """
    __tablename__ = "requirement_module"

    # ── v1.0 base ──
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(default=0, index=True)
    release_bundle_id: Mapped[int] = mapped_column(
        ForeignKey("release_bundle.id", ondelete="CASCADE"), index=True
    )

    name: Mapped[str] = mapped_column(String(500), default="")
    node_type: Mapped[str] = mapped_column(
        String(50), default="module", index=True
    )  # module | page | function_point | attachment
    platform: Mapped[str] = mapped_column(
        String(20), default="", index=True
    )  # APP | PC | WEB | ADMIN （用户端三端 + 运营后台）

    lanhu_page_id: Mapped[str] = mapped_column(
        String(500), default=""
    )  # stable id from Lanhu across versions
    change_type: Mapped[str] = mapped_column(
        String(30), default="new"
    )  # new | modified | deleted | unchanged

    # ── v1.1: version evolution ──
    parent_module_id: Mapped[int | None] = mapped_column(
        ForeignKey("requirement_module.id", ondelete="SET NULL"),
        default=None, index=True,
    )  # same module in parent version, forming cross-version evolution chain
    source_version: Mapped[str] = mapped_column(
        String(50), default=""
    )  # version string where this node first appeared

    screenshot_urls: Mapped[str] = mapped_column(
        Text, default="[]"
    )  # JSON array of screenshot URLs from Lanhu evidence pack
    has_visual_only_content: Mapped[bool] = mapped_column(
        default=False
    )  # True when interactions only visible in screenshots

    # ── v1.2: page interaction links ──
    page_interactions: Mapped[str] = mapped_column(
        Text, default="[]"
    )  # JSON array, valid when node_type="page"
    # Schema: [{
    #   "trigger": "点击搜索图标", "target_page": "搜索页",
    #   "interaction_type": "navigation|modal|tab_switch|external|dynamic_filter|global_navigation",
    #   "source_element": "顶部搜索栏",
    #   "admin_config_source": "资讯分类配置"  # only for dynamic_filter
    # }]


class ModuleAdminLink(Base, TimestampMixin):
    """Cross-system link between client-side modules and admin-backend modules.

    Supports two relation types:
      - links_to_admin: functional correspondence (module-level)
      - configures: admin config controls client runtime behavior (v1.3)
    """
    __tablename__ = "module_admin_link"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(default=0, index=True)

    client_module_id: Mapped[int] = mapped_column(
        ForeignKey("requirement_module.id", ondelete="CASCADE"), index=True
    )
    admin_module_id: Mapped[int] = mapped_column(
        ForeignKey("requirement_module.id", ondelete="CASCADE"), index=True
    )

    relation_type: Mapped[str] = mapped_column(
        String(50), default="links_to_admin", index=True
    )  # links_to_admin | configures

    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    evidence: Mapped[str] = mapped_column(Text, default="")  # human-readable rationale

    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
