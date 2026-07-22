"""ReleaseBundle / RequirementModule / ModuleAdminLink Pydantic schemas —— 发布包与模块树 DTO。

为 M3 API 层提供请求/响应模型。涵盖：
  - ReleaseBundle CRUD（创建/更新/详情/列表）
  - RequirementModule 模块树（节点/层级视图）
  - ModuleAdminLink 跨系统配置关联
"""
from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


# ═══════════════════════════════════════════════════════
# ReleaseBundle
# ═══════════════════════════════════════════════════════

class ReleaseBundleCreate(BaseModel):
    """创建发布包请求体。"""
    name: str = Field(..., min_length=1, max_length=500, description="发布包名称（通常与版本号关联）")
    description: str = Field("", description="发布包描述")
    client_version: str = Field("", max_length=100, description="用户端版本号，如 14.1.0")
    admin_version: str = Field("", max_length=100, description="运营后台版本号，如 8.2.0")
    release_date: date | None = Field(None, description="发布日期")
    parent_bundle_id: int | None = Field(None, description="父发布包 ID，形成版本链")


class ReleaseBundleUpdate(BaseModel):
    """更新发布包请求体（所有字段可选）。"""
    name: str | None = Field(None, max_length=500)
    description: str | None = None
    client_version: str | None = Field(None, max_length=100)
    admin_version: str | None = Field(None, max_length=100)
    status: str | None = Field(None, description="draft / active / archived")
    release_date: date | None = None
    parent_bundle_id: int | None = None
    diff_summary: str | None = Field(None, description="版本差异摘要 JSON")


class ReleaseBundleOut(BaseModel):
    """发布包完整响应体。"""
    id: int
    project_id: int
    name: str
    description: str
    client_version: str
    admin_version: str
    status: str
    release_date: date | None = None
    parent_bundle_id: int | None = None
    diff_summary: str = "{}"
    global_navigation: str = "[]"
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class ReleaseBundleListItem(BaseModel):
    """发布包列表项（轻量视图，含模块数统计）。"""
    id: int
    name: str
    client_version: str
    admin_version: str
    status: str
    release_date: date | None = None
    parent_bundle_id: int | None = None
    module_count: int = 0
    page_count: int = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class ReleaseBundleVersionChain(BaseModel):
    """版本链视图：从当前发布包追溯到最早版本。"""
    id: int
    name: str
    client_version: str
    admin_version: str
    status: str
    release_date: date | None = None
    parent_bundle_id: int | None = None

    model_config = ConfigDict(from_attributes=True)


class VersionDiffRequest(BaseModel):
    """触发版本差异对比请求体。"""
    parent_bundle_id: int = Field(..., description="父发布包 ID（上一版本）")
    source_version: str = Field("", description="源版本标识")


class VersionDiffConfirmRequest(BaseModel):
    """确认版本差异并构建模块树请求体。"""
    overrides: dict | None = Field(None, description="人工修正：{'reclassify': {module_name: new_type}, 'skip_modules': [name, ...]}")


# ═══════════════════════════════════════════════════════
# RequirementModule
# ═══════════════════════════════════════════════════════

class RequirementModuleOut(BaseModel):
    """需求模块节点完整响应体。"""
    id: int
    project_id: int
    release_bundle_id: int
    name: str
    node_type: str
    platform: str
    lanhu_page_id: str
    change_type: str
    parent_module_id: int | None = None
    source_version: str
    description: str = ""
    screenshot_urls: str = "[]"
    has_visual_only_content: bool = False
    page_interactions: str = "[]"
    sort_order: int = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class RequirementModuleBrief(BaseModel):
    """需求模块列表项（轻量视图）。"""
    id: int
    name: str
    node_type: str
    platform: str
    change_type: str
    parent_module_id: int | None = None
    description: str = ""
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class ModuleTreeNode(BaseModel):
    """模块树节点（递归结构，用于前端树形组件）。"""
    id: int
    name: str
    node_type: str  # module / page / function_point / attachment
    platform: str
    change_type: str
    description: str = ""
    lanhu_page_id: str = ""
    page_interactions: str = "[]"
    children: list[ModuleTreeNode] = Field(default_factory=list)
    child_count: int = 0  # 直接子节点数


class ModuleTreeResponse(BaseModel):
    """完整模块树响应。"""
    bundle_id: int
    bundle_name: str
    client_version: str
    admin_version: str
    roots: list[ModuleTreeNode] = Field(default_factory=list)
    total_modules: int = 0
    total_pages: int = 0
    total_attachments: int = 0


class ModuleExtractRequest(BaseModel):
    """触发模块树提取请求体。"""
    evidence_job_id: int = Field(..., description="LanhuEvidenceJob ID")
    document_id: int | None = Field(None, description="关联的 RequirementDocument ID")
    source_version: str = Field("", description="版本标识")


class ModuleExtractResult(BaseModel):
    """模块提取响应体。"""
    module_ids: list[int] = Field(default_factory=list)
    module_count: int = 0
    page_count: int = 0
    attachment_count: int = 0
    changelog_entries: int = 0
    warnings: list[str] = Field(default_factory=list)


# ═══════════════════════════════════════════════════════
# ModuleAdminLink
# ═══════════════════════════════════════════════════════

class ModuleAdminLinkOut(BaseModel):
    """跨系统（用户端↔运营后台）模块关联响应体。"""
    id: int
    project_id: int
    client_module_id: int
    admin_module_id: int
    relation_type: str
    confidence: float
    evidence: str
    metadata_json: str = "{}"
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class ModuleAdminLinkCreate(BaseModel):
    """手动创建跨系统模块关联请求体。"""
    client_module_id: int
    admin_module_id: int
    relation_type: str = "configures"


class ConfiguresLinkRequest(BaseModel):
    """触发配置关联分析请求体。"""
    client_version: str = Field("", description="用户端版本号")
    admin_version: str = Field("", description="运营后台版本号")


class ConfiguresLinkConfirmRequest(BaseModel):
    """确认配置关联并入库请求体。"""
    suggestion_indices: list[int] = Field(default_factory=list, description="要确认的 suggestion 索引列表（空=全部确认）")
    min_confidence: float = Field(0.5, ge=0, le=1, description="最低置信度阈值")


# ═══════════════════════════════════════════════════════
# Test Case Linking
# ═══════════════════════════════════════════════════════

class TestLinkingResult(BaseModel):
    """测试用例关联结果。"""
    linked_count: int = 0
    relations_created: int = 0
    by_strategy: dict[str, int] = Field(default_factory=dict)
    unmatched_cases: list[int] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class ModuleTestSummaryOut(BaseModel):
    """模块测试覆盖摘要。"""
    module_id: int
    module_name: str
    total_test_cases: int = 0
    functional: int = 0
    api: int = 0
    automation: int = 0
    coverage_rate: float = 0.0
    last_run_status: str = "unknown"
    linked_case_ids: list[int] = Field(default_factory=list)


# ═══════════════════════════════════════════════════════
# Interaction / Navigation
# ═══════════════════════════════════════════════════════

class InteractionExtractRequest(BaseModel):
    """触发页面交互提取请求体。"""
    preferred_layers: list[str] | None = Field(None, description="自定义降级链顺序，如 ['dom', 'ai', 'cv']")


class InteractionSaveRequest(BaseModel):
    """手动保存页面交互请求体。"""
    interactions: list[dict] = Field(default_factory=list)
    merge: bool = Field(True, description="合并到现有交互（False=替换）")


class GlobalNavClassifyRequest(BaseModel):
    """触发全局导航分类请求体。"""
    threshold: float = Field(0.80, ge=0.5, le=1.0, description="页面覆盖率阈值（默认 80%）")


class GlobalNavItemOut(BaseModel):
    """全局导航项。"""
    trigger: str
    target_page: str
    interaction_type: str = "global_navigation"
    coverage: float = 1.0
    source_element: str = ""
    description: str = ""


# ═══════════════════════════════════════════════════════
# Attachment Extraction
# ═══════════════════════════════════════════════════════

class AttachmentExtractRequest(BaseModel):
    """触发附件内容提取请求体。"""
    version: str = Field("", description="版本标识")


class AttachmentExtractResultOut(BaseModel):
    """附件提取结果。"""
    total_attachments: int = 0
    processed: int = 0
    failed: int = 0
    business_rules_created: int = 0
    function_points_extracted: int = 0
    errors: list[str] = Field(default_factory=list)


# ═══════════════════════════════════════════════════════
# Wiki Sync (for the sync router additions)
# ═══════════════════════════════════════════════════════

class WikiSyncRequest(BaseModel):
    """触发 Wiki 同步请求体。"""
    create_wiki_pages: bool = Field(False, description="是否同时触发 Wiki 页面编译")


class WikiSyncResultOut(BaseModel):
    """Wiki 同步结果。"""
    release_bundle_id: int
    raw_sources_created: int = 0
    raw_sources_updated: int = 0
    raw_sources_skipped: int = 0
    coverage: dict = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)


class WikiTreeDiffOut(BaseModel):
    """模块树 vs Wiki 差异对比结果。"""
    only_in_tree: list[str] = Field(default_factory=list)
    only_in_wiki: list[str] = Field(default_factory=list)
    in_both: int = 0
    total_tree_pages: int = 0
    total_wiki_pages: int = 0


# ═══════════════════════════════════════════════════════
# Knowledge Graph Hierarchy (Project Sphere)
# ═══════════════════════════════════════════════════════

class ProjectSphereNode(BaseModel):
    """项目球节点（用于层级图谱可视化）。"""
    id: str  # 稳定标识，如 "project:1", "bundle:3", "module:15"
    name: str
    node_type: str  # project / version / platform / module / page / attachment / admin_module
    parent_id: str | None = None
    version: str = ""  # 所属版本
    platform: str = ""  # APP / PC / WEB / ADMIN
    change_type: str = ""  # new / modified / deleted / unchanged
    metadata: dict = Field(default_factory=dict)


class ProjectSphereEdge(BaseModel):
    """项目球关系边。"""
    source: str  # node id
    target: str  # node id
    relation_type: str  # contains / configures / tested_by / navigates_to / described_by
    confidence: float = 1.0
    label: str = ""


class ProjectSphereView(BaseModel):
    """项目球完整视图。"""
    project_id: int
    project_name: str = ""
    nodes: list[ProjectSphereNode] = Field(default_factory=list)
    edges: list[ProjectSphereEdge] = Field(default_factory=list)
    stats: dict = Field(default_factory=dict)  # {versions, modules, pages, relations}
