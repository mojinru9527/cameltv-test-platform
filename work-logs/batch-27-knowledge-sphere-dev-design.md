# Batch 27 — Dev 技术架构设计
> **Dev (💻)** | Date: 2026-07-22 | Updated: 2026-07-22 (v1.3 — interaction 枚举补全 + 全局导航 + configures 关系 + 附件结构化 + 降级提取)
> Type: 架构设计（非代码交付批次）

## 0. 架构总览

```
┌──────────────────────────────────────────────────────────────────┐
│                        蓝湖 .rp 文档                               │
│              用户原型需求.rp  │  运营后台.rp                        │
└──────────────┬────────────────────┬──────────────────────────────┘
               │                    │
               ▼                    ▼
┌──────────────────────────────────────────────────────────────────┐
│            LanhuEvidenceJob (证据采集+OCR+截图)                    │
│            产出: 页面列表 + OCR文本 + 页面截图                      │
└──────────────┬────────────────────┬──────────────────────────────┘
               │                    │
               ▼                    ▼
┌──────────────────────────────────────────────────────────────────┐
│           版本 Diff 引擎 (v2+ 增量导入) — 🆕 v1.1                  │
│  v1: 全量提取基线    v2+: 与父版本 Diff → 仅提取变更模块           │
└──────────────────────────┬───────────────────────────────────────┘
               │                    │
               ▼                    ▼
┌──────────────────────────────────────────────────────────────────┐
│              ReleaseBundle (发布包) — 增强模型                     │
│  聚合: 用户端版本 + 运营后台版本 + 说明附件 + 版本链(parent)       │
└──────────┬──────────┬──────────┬──────────┬──────────────────────┘
           │          │          │          │
           ▼          ▼          ▼          ▼
    ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐
    │ APP 模块  │ │ PC 模块   │ │ WEB 模块  │ │ 运营后台模块      │
    │ ├ 页面    │ │ ├ 页面   │ │ ├ 页面   │ │ ├ 功能页面        │
    │ ├ 截图 🆕 │ │ ├ 截图   │ │ ├ 截图   │ │ ├ 截图 🆕        │
    │ └ 用例 🆕 │ │ └ 用例   │ │ └ 用例   │ │ └ 用例 🆕        │
    └──────────┘ └──────────┘ └──────────┘ └──────────────────┘
           │          │          │          │
           └──────────┴──────────┴──────────┘
                      │
                      ▼
┌──────────────────────────────────────────────────────────────────┐
│                  KnowledgeEntity + KnowledgeRelation               │
│                  「项目球」层级图谱                                 │
│                                                                   │
│  层级: Project → ReleaseBundle → Platform → Module → Page         │
│                                                       │           │
│                                           ┌──────────┴──────┐    │
│                                           │  TestCase 叶子   │ 🆕 │
│                                           │  (功能/API/自动化)│    │
│  跨端: Module ──links_to_admin──→ AdminModule                     │
│  演化: Module(v1) ──evolves_from──→ Module(v2)                    │
│  用例: Module ──tested_by──→ TestCase(功能/API/自动化) 🆕          │
│  跳转: Page ──navigates_to──→ Page (交互链路) 🆕 v1.2              │
│  配置: Module ──configures──→ AdminModule (跨系统配置链路) 🆕 v1.3  │
└──────────────────────────────────────────────────────────────────┘
```

## 1. 数据模型设计

### 1.1 新增模型: `RequirementModule`

**目的**：将 `RequirementDocument` 的扁平内容结构化，表达"模块→页面→功能点"层级。

```python
class RequirementModule(Base, TimestampMixin):
    """蓝湖需求文档中的模块节点 — 对应蓝湖文件夹/页面结构"""
    __tablename__ = "requirement_module"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("requirement_document.id"), index=True)
    parent_id: Mapped[int | None] = mapped_column(default=None, index=True)  # 父模块（树形结构）
    # module / page / attachment
    # 🆕 v1.2: attachment 类型仅在少数大模块中存在（广告位/银钻/UGC/付费活动/骆驼币及绿钻等），
    #   并非每个模块都有说明附件。导入时附件缺失为正常情况，不报错。
    node_type: Mapped[str] = mapped_column(default="module", index=True)
    name: Mapped[str] = mapped_column(default="")
    description: Mapped[str] = mapped_column(Text, default="")
    # APP / PC / WEB / admin — 从蓝湖文件夹自动提取
    platform: Mapped[str] = mapped_column(default="", index=True)
    sort_order: Mapped[int] = mapped_column(default=0)  # 同级排序
    lanhu_page_id: Mapped[str] = mapped_column(default="")  # 蓝湖页面 ID，用于跳转
    change_type: Mapped[str] = mapped_column(default="new")  # new/modified/unchanged/deleted (版本 diff)

    # === 🆕 v1.1: 版本演化链 ===
    parent_module_id: Mapped[int | None] = mapped_column(default=None, index=True)
    # → 同一模块在父版本中的 ID，形成跨版本演化链
    # 例: v2.5.0 "资讯" 的 parent_module_id → v2.0.0 "资讯"
    # null = 本模块是首次引入（新模块）

    source_version: Mapped[str] = mapped_column(default="")
    # → 该节点被首次引入的版本号
    # 对于 v2+ 的 modified 节点，source_version 仍是首次引入的版本

    # === 🆕 v1.1: 截图保留 ===
    screenshot_urls: Mapped[str] = mapped_column(Text, default="[]")
    # → JSON 数组，存储该模块/页面在蓝湖中的截图 URL 列表
    # 例: ["https://lanhu-app.oss-cn-beijing.aliyuncs.com/xxx.png", ...]
    # 证据包导入时自动从 LanhuEvidencePage.screenshot_url 关联填充

    has_visual_only_content: Mapped[bool] = mapped_column(default=False)
    # → 标记该页面是否有仅通过截图才能理解的交互（如动效、弹窗、状态切换）
    # AI 分析截图时设置；为 True 时前端显示 "📸 含视觉交互" 标记

    # === 🆕 v1.2/v1.3: 页面交互跳转链路 ===
    page_interactions: Mapped[str] = mapped_column(Text, default="[]")
    # → JSON 数组，记录页面内的交互热点及跳转目标（node_type="page" 的节点，含用户端和运营后台端）
    # 🆕 v1.3: 运营后台页面同样适用此字段
    # 蓝湖原型中的可点击区域（按钮、链接、导航栏等）在导出时不会自动保留，
    # 但这些交互关系对理解完整需求和生成测试用例至关重要。
    # 例:
    # [
    #   {
    #     "trigger": "点击搜索图标",
    #     "target_page": "搜索页",
    #     "target_lanhu_page_id": "xxx",
    #     "interaction_type": "navigation",  # navigation / modal / tab_switch / external / dynamic_filter / global_navigation
    #     "source_element": "顶部搜索栏",
    #     "description": "用户在资讯列表页点击搜索图标，跳转至搜索页面"
    #   },
    #   {
    #     "trigger": "点击资讯分类Tab",
    #     "target_page": "分类筛选页",
    #     "target_lanhu_page_id": "",
    #     "interaction_type": "dynamic_filter",  # 🆕 v1.3: 目标内容由运营后台配置决定
    #     "source_element": "分类Tab栏",
    #     "admin_config_source": "运营后台-资讯分类配置",  # 🆕 v1.3: 关联的后台配置项
    #     "description": "分类Tab的内容由运营后台配置，非固定页面"
    #   },
    #   {
    #     "trigger": "点击资讯卡片",
    #     "target_page": "资讯详情页",
    #     "target_lanhu_page_id": "yyy",
    #     "interaction_type": "navigation",
    #     "source_element": "资讯列表项",
    #     "description": "点击任意资讯条目进入详情页"
    #   }
    # ]
    # 🆕 v1.3 全局导航规则:
    #   - 自动判断: 如果同一 trigger+target 出现在 >80% 的页面中 → 归类为 global_navigation
    #   - global_navigation 提升到 ReleaseBundle.global_navigation 字段存储（不逐页重复）
    #   - 图谱中全局导航用浅蓝虚线统一渲染
    # 🆕 v1.3 版本演化规则:
    #   - modified 页面 = 强制重新提取 page_interactions（旧数据不继承）
    #   - navigates_to 边优先匹配同版本页面；同版本无则匹配最近父版本节点
    # 来源: 蓝湖 HTML DOM 抓取 + AI 多模态分析 + 手动补充
    # 用途: (a) 知识图谱 navigates_to 关系 (b) AI 测试用例扩展 (c) 版本全景中的页面跳转图
```

### 1.2 新增模型: `ReleaseBundle`

**目的**：聚合用户端版本 + 运营后台版本 + 说明附件为一个"完整发布"。

```python
class ReleaseBundle(Base, TimestampMixin):
    """发布包 — 聚合一个完整版本的用户端+运营后台需求"""
    __tablename__ = "release_bundle"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(index=True)
    name: Mapped[str] = mapped_column(default="")        # 如 "体育平台 v3.0.0 发布"
    # 用户端版本号（来自蓝湖更新日志）
    client_version: Mapped[str] = mapped_column(default="", index=True)
    # 运营后台版本号（来自蓝湖运营后台更新日志，可为空=本版本无运营后台变更）
    admin_version: Mapped[str] = mapped_column(default="")
    release_date: Mapped[datetime | None] = mapped_column(default=None)
    description: Mapped[str] = mapped_column(Text, default="")

    # 关联的蓝湖文档
    client_doc_id: Mapped[int | None] = mapped_column(default=None)   # → requirement_document.id (用户端)
    admin_doc_id: Mapped[int | None] = mapped_column(default=None)    # → requirement_document.id (运营后台)
    # draft / published / archived
    status: Mapped[str] = mapped_column(default="draft", index=True)
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")

    # === 🆕 v1.1: 版本链（增量导入） ===
    parent_bundle_id: Mapped[int | None] = mapped_column(default=None, index=True)
    # → 上一个版本的 ReleaseBundle ID，形成版本链
    # v1.0 的 parent_bundle_id = None (基线版本)
    # v2.0 的 parent_bundle_id → v1.0 的 ReleaseBundle
    # 用于版本 Diff：导入时自动与 parent 对比，识别变更模块

    diff_summary: Mapped[str] = mapped_column(Text, default="{}")
    # → JSON，记录与父版本的差异摘要：
    # {
    #   "new_modules": ["直播"],        // 本版本新增的模块
    #   "modified_modules": ["资讯"],    // 本版本修改的模块（含修改的页面列表）
    #   "deleted_modules": [],          // 本版本删除的模块
    #   "unchanged_modules": ["用户", "个人中心"],  // 未变更模块（跳过提取）
    #   "total_pages_diff": +5,         // 页面数变化
    #   "diff_confidence": 0.85         // AI 判断的置信度
    # }

    # === 🆕 v1.3: 全局导航 ===
    global_navigation: Mapped[str] = mapped_column(Text, default="[]")
    # → JSON 数组，记录跨页面的全局导航项（如底部 Tab 栏、顶部导航栏）
    # 自动判断规则: 同一 trigger+target 出现在 >80% 的页面中 → 全局导航
    # 不从逐页 page_interactions 中重复存储，统一提升到此字段
    # 例:
    # [
    #   {"trigger": "点击底部Tab-首页", "target_page": "首页", "interaction_type": "global_navigation"},
    #   {"trigger": "点击底部Tab-我的", "target_page": "个人中心", "interaction_type": "global_navigation"},
    #   {"trigger": "点击底部Tab-预测", "target_page": "预测页", "interaction_type": "global_navigation"}
    # ]
    # 图谱渲染: 全局导航边从 Platform 节点统一引出（而非逐页），浅蓝色虚线
```

### 1.3 新增模型: `ModuleAdminLink`

**目的**：显式建模用户端模块↔运营后台模块的关联关系。

```python
class ModuleAdminLink(Base, TimestampMixin):
    """用户端模块 ↔ 运营后台模块 关联"""
    __tablename__ = "module_admin_link"

    id: Mapped[int] = mapped_column(primary_key=True)
    release_bundle_id: Mapped[int] = mapped_column(ForeignKey("release_bundle.id"), index=True)
    client_module_id: Mapped[int] = mapped_column(ForeignKey("requirement_module.id"), index=True)
    admin_module_id: Mapped[int] = mapped_column(ForeignKey("requirement_module.id"), index=True)
    # manual / ai_suggested / confirmed
    link_source: Mapped[str] = mapped_column(default="manual")
    confidence: Mapped[float] = mapped_column(default=1.0)  # AI 建议的置信度
    notes: Mapped[str] = mapped_column(Text, default="")
```

### 1.4 现有模型变更（最小侵入）

**`RequirementDocument` 扩展**：
```python
# 新增字段
platform: Mapped[str] = mapped_column(default="")        # APP/PC/WEB/admin (单文档可能只对应一个端)
doc_type: Mapped[str] = mapped_column(default="rp")      # rp/xlsx/docx/md — 区分蓝湖原型 vs 其他需求文档
```

**`KnowledgeSource` 扩展**：
```python
# 新增字段 — 关联到模块层级
module_id: Mapped[int | None] = mapped_column(default=None, index=True)  # → requirement_module.id
```

**知识图谱实体类型扩展**（不需要改表，`entity_type` 是字符串）：
```
现有: project, service, module, api, field, requirement, rule, test_case, defect, iteration
新增: release_bundle, platform, client_module, admin_module, page, changelog_entry, attachment
```

**关系类型扩展**（不需要改表，`relation_type` 是字符串）：
```
现有: affects, contains, has_field, covers, exposes, depends_on, generated_from, executed_by
新增: belongs_to_version, has_platform, has_module, has_page, links_to_admin, evolves_from, described_by
🆕 v1.2: navigates_to (Page→Page 交互跳转链路)
🆕 v1.3: configures (client_module→admin_module 跨系统配置链路)
```

### 1.6 实体 Key 设计规范 (v1.1 修订)

为保证实体唯一性，`entity_key` 遵循以下格式（已按 QA D1 建议加入版本号）：

```
# 项目球层级
project:{project_name}
release_bundle:{project_name}:{client_version}
platform:{project_name}:{client_version}:{platform}         # platform=APP/PC/WEB
client_module:{project_name}:{client_version}:{module_name} # 🆕 含版本号，避免同名模块冲突
admin_module:{project_name}:{admin_version}:{module_name}
page:{project_name}:{module_name}:{page_name}
changelog_entry:{project_name}:{version}:{entry_index}
attachment:{project_name}:{version}:{file_name}

# 测试用例关联 (🆕 v1.1)
test_case:{test_case_id}  # 复用现有 test_case 实体

# 跨端关联 (实体 Key 不变，通过 relation 连接)
relation: links_to_admin (from client_module → to admin_module)
relation: tested_by (from module/page → to test_case)      # 🆕 v1.1
relation: navigates_to (from page → to page)               # 🆕 v1.2 页面交互跳转
relation: configures (from client_module → to admin_module) # 🆕 v1.3 跨系统配置链路
```

---

## 1.7 🆕 版本增量导入引擎 v1.1

### 1.7.1 核心理念

```
v1 (基线版本):  全量导入 → 提取所有模块/页面 → 全部标记 change_type="new"
v2+ (增量版本): 提交时与父版本 Diff → 仅提取变更模块 → 未变更模块跳过功能拆分和用例生成
```

### 1.7.2 Diff 引擎设计

```python
# backend/app/services/knowledge/version_differ.py

@dataclass
class VersionDiffResult:
    """版本差异分析结果"""
    new_modules: list[str]          # 本版本新增的模块名列表
    modified_modules: list[ModuleChange]  # 本版本修改的模块
    deleted_modules: list[str]      # 本版本删除的模块名列表
    unchanged_modules: list[str]    # 未变更模块（跳过提取）
    diff_confidence: float          # AI 判断置信度

@dataclass
class ModuleChange:
    module_name: str
    parent_module_id: int           # 父版本中同模块的 ID
    new_pages: list[str]            # 新增页面
    modified_pages: list[str]       # 修改页面
    deleted_pages: list[str]        # 删除页面
    unchanged_pages: list[str]      # 未变更页面


class VersionDiffer:
    """版本差异分析器"""

    async def diff(
        self,
        current_doc: RequirementDocument,
        parent_bundle: ReleaseBundle,
    ) -> VersionDiffResult:
        """
        对比当前版本与父版本的模块差异。

        Phase A — 规则引擎（快速路径）:
        1. 从 lanhu_evidence_page 获取当前版本的页面列表 (by folder → page)
        2. 从父版本的 requirement_module 获取已有模块树
        3. 规则匹配：
           - 文件夹名完全相同 → 同一模块 (modified/unchanged)
           - 父版本有、当前版本无 → deleted
           - 当前版本有、父版本无 → new
        4. 同级页面名对比：新增/删除/同名(不变)

        Phase B — AI 辅助（规则无法覆盖时）:
        1. DeepSeek 分析页面 OCR 内容相似度
        2. 模块名模糊匹配 (如 "资讯模块" ↔ "资讯管理")
        3. 输出置信度

        关键规则：
        - 未变更模块 (unchanged_modules): 不提取、不拆分、不生成用例
        - 已变更模块 (new + modified): 提取页面内容 + 截图，但保留对父模块的引用
        - 修改模块的 unchanged_pages: 记录但不重新提取内容
        """
        pass

    async def build_incremental_module_tree(
        self,
        diff_result: VersionDiffResult,
        parent_modules: list[RequirementModule],
        current_pages: list[LanhuEvidencePage],
    ) -> list[RequirementModule]:
        """
        基于 Diff 结果构建增量模块树。

        新增模块: 创建完整的模块→页面树，change_type="new"
        修改模块:
          - 复用父模块的 unchanged_pages (通过 parent_module_id 引用)
          - 仅创建 new_pages + modified_pages 节点
          - 设置 parent_module_id → 父版本同模块
        删除模块: 创建节点标记 change_type="deleted"（不生成用例）
        未变更模块: ⚠️ 不创建任何节点（前端从父版本拉取）
        """
        pass
```

### 1.7.3 版本导入流程 (修订)

```
┌─────────────────────────────────────────────────────────────┐
│                    版本需求导入流程                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Step 1: 用户上传/导入需求文档                                │
│     ↓                                                       │
│  Step 2: 选择版本类型                                        │
│     ├─ 🆕 基线版本 (v1) → 全量导入模式                        │
│     └─ 📦 增量版本 (v2+) → 选择父版本 → 增量导入模式          │
│     ↓                                                       │
│  Step 3: 版本 Diff (仅增量模式)                               │
│     ├─ 规则引擎: 文件夹/页面名称对比                           │
│     ├─ AI 辅助: OCR 内容相似度分析 (规则无法覆盖时)            │
│     └─ 产出: VersionDiffResult                              │
│     ↓                                                       │
│  Step 4: 人工审核 Diff 结果                                   │
│     ├─ 确认新增/修改/删除/未变更的模块列表                      │
│     ├─ 修正 AI 误判                                           │
│     └─ 确认后锁定                                            │
│     ↓                                                       │
│  Step 5: 增量提取 (仅变更模块)                                │
│     ├─ 提取 new_modules + modified_modules 的页面内容         │
│     ├─ 关联页面截图 (从证据包)                                │
│     ├─ ⏭️ 跳过 unchanged_modules                            │
│     └─ 产出: RequirementModule 节点列表                       │
│     ↓                                                       │
│  Step 6: 功能拆分 (仅变更模块的功能点)                         │
│     ├─ AI 分析页面 OCR + 截图 → 功能点列表                     │
│     ├─ ⚠️ 修改模块: 功能拆分时考虑父模块的已有功能作为上下文     │
│     └─ ⏭️ 未变更模块: 不拆分                                 │
│     ↓                                                       │
│  Step 7: 用例生成 (仅变更模块的功能点)                         │
│     ├─ 功能用例: 针对新增/修改的功能点                          │
│     ├─ 接口用例: 针对新增/修改的 API                           │
│     ├─ 自动化用例: 针对新增/修改的 UI 流程                      │
│     └─ ⏭️ 未变更模块: 不生成任何用例                           │
│     ↓                                                       │
│  Step 8: 创建 ReleaseBundle + 关联用例到模块                   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 1.7.4 关键设计决策

| 决策 | 说明 |
|------|------|
| 未变更模块不生成用例 | 旧版本的用例已经存在，不需要重复生成。如需回归测试，从父版本的用例中筛选 |
| 修改模块保留父模块上下文 | `parent_module_id` 链让前端能展示完整模块（父版本页面 + 本版本变更） |
| Diff 结果需人工确认 | AI 判断可能有误（如模块重命名），必须经过人工审核步骤 |
| v1 基线必须完整 | 增量导入的正确性依赖基线的完整性。如果基线缺失模块，后续 diff 会漏判 |

---

## 1.8 🆕 测试用例图谱关联 v1.1

### 1.8.1 关联模型

测试用例通过现有的 `KnowledgeRelation` 表连接到模块/页面节点：

```
Module/Page ──tested_by──→ TestCase
                           ├── test_case_type: functional / api / automation
                           ├── 现有字段: id, name, steps, expected_result...
                           └── 图谱节点: entity_type="test_case", 颜色区分类型
```

不需要新建表——利用现有 `KnowledgeRelation` 表，新增关系类型 `tested_by`：

```python
# relation_type 扩展 (字符串字段，无需 DDL)
# 现有: affects, contains, has_field, covers, exposes, depends_on, generated_from, executed_by
# 🆕 新增:
#   tested_by — Module/Page → TestCase (模块被哪些用例测试)

# 创建关联:
KnowledgeRelation(
    source_entity_key="client_module:CamelTv:v3.0.0:资讯",
    target_entity_key="test_case:TC-ZX-001",
    relation_type="tested_by",
)
```

### 1.8.2 自动关联策略

```python
# backend/app/services/knowledge/test_case_linker.py

class TestCaseLinker:
    """测试用例 ↔ 模块 自动关联器"""

    async def link_test_cases_to_module(
        self,
        module: RequirementModule,
        test_cases: list[TestCase],  # 本版本生成或已存在的用例
    ) -> list[KnowledgeRelation]:
        """
        策略优先级：
        1. 精确匹配: 用例名称中含模块名 (如 "资讯列表-展示验证" → "资讯"模块)
        2. 功能点匹配: 用例关联的 function_point 属于该模块
        3. API 匹配: 接口用例的 API endpoint 关联到该模块的页面
        4. 手动关联: 用户在版本全景视图中拖拽建立关联
        """
        pass

    async def get_module_test_summary(
        self,
        module_id: int,
    ) -> ModuleTestSummary:
        """
        获取模块的测试覆盖摘要：
        {
          "total_test_cases": 15,
          "functional": 8,    # 功能用例数
          "api": 5,           # 接口用例数
          "automation": 2,    # 自动化用例数
          "coverage_rate": 0.85,  # 功能点覆盖率
          "last_run_status": "passed"  # 最近一次执行结果
        }
        """
        pass
```

### 1.8.3 图谱可视化 (用例节点)

```
项目球层级:
  Project
    └── ReleaseBundle v3.0.0
          └── Platform: APP
                └── Module: 资讯
                      ├── Page: 资讯列表
                      │     ├── 🟢 TC-ZX-001 (功能) ← 🆕 叶子节点
                      │     ├── 🔵 TC-API-ZX-010 (接口) ← 🆕
                      │     └── 🟠 TC-AUTO-ZX-101 (自动化) ← 🆕
                      ├── Page: 资讯详情
                      │     ├── 🟢 TC-ZX-005 (功能)
                      │     └── 🟢 TC-ZX-006 (功能)
                      └── Page: 评论
                            └── 🟢 TC-ZX-008 (功能)

用例节点样式:
  🟢 功能用例:  绿色小圆点 #10b981, 图标 ClipboardCheck
  🔵 接口用例:  蓝色小圆点 #3b82f6, 图标 Server
  🟠 自动化用例: 橙色小圆点 #f97316, 图标 Play
```

### 1.8.4 auto-build 增强

在 `POST /api/v1/knowledge/graph/auto-build` 流程中追加测试用例关联步骤：

```
Step 5 (🆕): 关联测试用例
  - 对每个新增/修改的模块/页面
  - 查询已有用例 (按模块名 + 功能点匹配)
  - 查询新生成用例 (本版本刚生成的)
  - 建立 tested_by 关系
  - 用例节点挂在对应页面下方（叶子节点）
```

---

## 1.9 🆕 页面交互跳转链路 v1.2

### 1.9.1 背景

蓝湖原型中的交互热点（可点击区域、按钮、导航Tab 等）是需求的重要组成部分，但在文本导出时不会自动保留。用户在原型中的操作路径——如从资讯列表点击搜索→搜索页、点击资讯卡片→详情页、点击底部导航Tab→切换页面——这些跳转关系本身就是需求规格的一部分。

此前用户用"图片"描述的正是这些交互链路：蓝湖中的页面截图虽然可见，但**点击跳转关系**才是需要保留的核心信息。

### 1.9.2 数据模型

交互跳转数据存储在 `RequirementModule.page_interactions`（JSON 字段，仅对 `node_type="page"` 的节点有意义）：

```json
[
  {
    "trigger": "点击搜索图标",
    "target_page": "搜索页",
    "target_lanhu_page_id": "9f0a47f3...",
    "interaction_type": "navigation",
    "source_element": "顶部搜索栏",
    "description": "用户在资讯列表页点击搜索图标，跳转至搜索页面"
  }
]
```

`interaction_type` 枚举：
| 类型 | 说明 | 示例 |
|------|------|------|
| `navigation` | 页面间跳转（目标为固定页面） | 列表→详情、搜索→结果 |
| `modal` | 弹窗/浮层 | 点击按钮→弹出确认框 |
| `tab_switch` | 底部导航/Tab 切换（非全局，仅特定页面） | 页面内 Tab 切换（如"正在进行/已结束"） |
| `external` | 外部链接 | 跳转到第三方支付页面 |
| `dynamic_filter` 🆕 v1.3 | 目标内容由后台配置决定，非固定页面 | 资讯分类Tab（分类由运营后台配置） |
| `global_navigation` 🆕 v1.3 | 全局导航项（>80% 页面共有），提升到 ReleaseBundle 存储 | 底部导航栏（首页/我的/预测） |

### 1.9.3 提取策略（四层降级）🆕 v1.3

```
优先级 1 — 蓝湖原型 HTML DOM 抓取 (自动) 🆕 v1.3:
  - 蓝湖原型本质是 Axure 导出的 HTML，可点击元素在 DOM 中有 link/hotspot 标记
  - 通过 lanhu-mcp 打开原型页面后直接解析 DOM，提取：
    · <a> 标签的 href 目标
    · 元素的 data-click/data-link 等自定义属性
    · Axure 的 hotspot 组件标记
  - 比截图分析更可靠（不需要"猜"什么是可点击的）
  - ⚠️ 需验证 lanhu-mcp 能否稳定获取原型页面的 DOM

优先级 2 — AI 多模态截图分析 (自动):
  - DeepSeek 多模态分析蓝湖页面截图
  - 识别可交互元素（按钮、输入框、导航栏、列表项、Tab）
  - 根据上下文推断跳转目标页面
  - 产出: page_interactions JSON
  - ⚠️ 准确率依赖模型能力，M1 前需 POC 验证（5 页 ground truth 对比）

优先级 3 — CV 启发式检测 + OCR 文字分析 (自动) 🆕 v1.3:
  - OpenCV 检测常见 UI 模式：底部导航栏（屏幕底部固定区域）、搜索图标（放大镜形状）、
    列表项（重复的矩形区域）、返回按钮（左上角箭头）
  - OCR 提取所有文字，匹配动作词（搜索/提交/确认/返回/首页/我的）
  - 结合位置信息推断功能类型
  - 作为优先级 1/2 均不可用时的降级自动方案

优先级 4 — 手动标注 (兜底):
  - 在版本全景视图中，提供截图标注 UI：
    · 在截图上框选热区 → 下拉选择目标页面 → 选择交互类型
  - 支持批量操作（如"所有页面都有底部Tab"一键标记）
  - 标注结果即时回写到 page_interactions JSON
```

### 1.9.4 知识图谱关系

```
Page: 资讯列表 ──navigates_to──→ Page: 搜索页      (点击搜索图标)
Page: 资讯列表 ──navigates_to──→ Page: 资讯详情页    (点击资讯卡片)
Page: 资讯列表 ──navigates_to──→ Page: 个人中心      (底部Tab切换)
Page: 资讯列表 ──navigates_to──→ Page: 首页          (底部Tab切换)
Page: 资讯列表 ──navigates_to──→ Page: 预测页        (底部Tab切换)
```

图谱中 `navigates_to` 关系特点：
- **弱关联边**：虚线 + 浅色（与层级关系、跨端关联区分）
- **方向箭头**：单向（A→B）
- **悬浮标签**：hover 时显示 `trigger` 文本（如 "点击搜索图标"）
- **默认折叠**：在项目球视图中，navigates_to 边默认隐藏，用户勾选"显示页面跳转"后展示

### 1.9.5 AI 测试用例扩展

`page_interactions` 数据在生成测试用例时注入 AI prompt，扩展测试覆盖范围：

```
生成功能用例时的额外上下文：
"该页面存在以下交互跳转关系：
1. 点击搜索图标 → 搜索页
2. 点击资讯卡片 → 资讯详情页
3. 底部Tab → 首页/我的/预测

请针对以上交互链路生成对应的导航测试用例，包括：
- 跳转目标是否正确
- 跳转后返回是否正常
- 边界情况（如搜索关键词为空时点击搜索）"
```

生成的测试用例类型扩展：
| 原有用例类型 | 扩展覆盖 |
|-------------|---------|
| 页面展示验证 | + 交互元素存在性验证（搜索图标、Tab 是否可见） |
| 功能流程验证 | + 页面跳转流程验证（A→B→返回A） |
| 边界验证 | + Tab 切换状态保持、深层跳转后一键返回 |
| — | + **新增**: 导航链路完整性测试（所有 `navigates_to` 边遍历） |

### 1.9.6 auto-build 增强

在 `POST /api/v1/knowledge/graph/auto-build` 流程中追加交互链路构建步骤：

```
Step 6 (🆕 v1.2/v1.3): 构建页面跳转关系
  - 遍历所有 page 节点的 page_interactions JSON
  - 🆕 v1.3: 先执行全局导航分类——统计所有页面的交互，
    同一 trigger+target 出现率 >80% → 提升到 ReleaseBundle.global_navigation
  - 匹配 target_page 到已知页面节点:
    · 优先匹配同版本页面
    · 同版本无 → 匹配最近父版本节点
    · 仍未匹配 → 输出"未匹配"列表，提示手动关联
  - 建立 navigates_to 关系（non-global）
  - 为每个 navigates_to 边生成描述性 label (取自 trigger 字段)
  - 🆕 v1.3: 对 admin 端页面同样执行上述流程
```

### 1.9.7 版本演化与跨版本匹配 🆕 v1.3

**modified 页面强制重提取**：
- 当页面标记为 `change_type="modified"` 时，旧版本的 `page_interactions` **不继承**
- 系统对该页面重新执行提取策略，因为页面布局/交互可能已改变
- `new` 页面：全量提取
- `unchanged` 页面：从父版本继承 page_interactions

**navigates_to 跨版本匹配规则**：
```
优先匹配同版本 target_page:
  v3.0/资讯列表 → v3.0/搜索页          ✅ 同版本，直接匹配

同版本无 → 匹配最近父版本节点:
  v3.0/资讯列表 → v2.0/搜索页          ✅ v3.0 中搜索页 unchanged，回退到 v2.0 节点

父版本也无 → 未匹配:
  v3.0/资讯列表 → ???/第三方支付页      ⚠️ 输出到未匹配列表，提示手动关联或创建节点
```

**admin 端页面同样适用**：
- 运营后台页面也使用 `page_interactions` 字段
- 运营后台典型交互：用户列表→用户详情→编辑用户；资讯管理→资讯审核→审核通过/拒绝
- 图谱中 admin 端的 navigates_to 边与用户端使用相同的视觉约定

### 1.9.8 全局导航自动分类 🆕 v1.3

**判定规则**：
```
IF 同一 (trigger, target_page) 组合出现在 >80% 的页面中:
  → interaction_type = "global_navigation"
  → 从逐页 page_interactions 中移除
  → 提升到 ReleaseBundle.global_navigation 存储
```

**为什么 80%**：并非 100% 的页面都有底部导航栏（如全屏播放页、弹窗页可能没有），80% 阈值允许合理容差。

**图谱渲染差异**：
| 导航类型 | 存储位置 | 边来源 | 线条样式 |
|---------|---------|--------|---------|
| 普通页面跳转 | page.page_interactions | 从具体 Page 节点引出 | 灰色虚线 |
| 全局导航 | ReleaseBundle.global_navigation | 从 Platform 节点统一引出 | 浅蓝色虚线 |

**auto-build Step 6 增强**：
```
Step 6a (🆕 v1.3): 全局导航分类
  - 收集当前 ReleaseBundle 下所有 page 的 page_interactions
  - 按 (trigger, target_page) 分组统计出现次数
  - 出现率 >80% → 移入 ReleaseBundle.global_navigation
  - 其余保留在各自 page.page_interactions 中
```

---

## 1.10 🆕 configures 跨系统配置链路 v1.3

### 1.10.1 背景

用户端功能的展示内容往往由运营后台配置决定。例如：
- 资讯列表页的「分类 Tab」→ 展示哪些分类由运营后台「资讯分类配置」决定
- 首页的「推荐内容」→ 由运营后台「推荐位管理」配置
- 直播间的「礼物列表」→ 由运营后台「礼物管理」配置

这种关系不是 `links_to_admin`（模块级功能对应），而是**"用户端功能的运行时行为由运营后台的某个配置项控制"**。将此关系纳入图谱有助于：
- 测试时理解：改了这个后台配置，会影响用户端哪些页面的展示？
- 需求追溯：这个用户端功能依赖哪些后台配置项？
- 故障排查：用户端显示异常 → 沿 `configures` 边反向追溯可能的配置问题

### 1.10.2 关系模型

```
client_module ──configures──→ admin_module
```

利用现有 `KnowledgeRelation` 表（无需 DDL），新增关系类型 `configures`：

```python
KnowledgeRelation(
    source_entity_key="client_module:CamelTv:v3.0.0:资讯",
    target_entity_key="admin_module:CamelTv:v4.0.0:资讯分类配置",
    relation_type="configures",
    metadata_json='{"config_items": ["分类名称", "分类排序", "是否启用"], "impact": "决定资讯列表页分类Tab的显示内容"}'
)
```

### 1.10.3 与 links_to_admin 的区别

| 维度 | links_to_admin | configures |
|------|---------------|-----------|
| 语义 | 功能对应（用户端的资讯模块对应运营后台的资讯管理） | 配置控制（后台配置项控制用户端页面的运行时行为） |
| 粒度 | 模块→模块 | 模块→模块（但强调配置控制关系） |
| 方向 | client_module → admin_module | client_module → admin_module |
| 图谱边样式 | 橙色虚线 | 紫色虚线（区分） |
| 测试影响 | 跨端功能完整性测试 | 配置变更影响面测试 |

### 1.10.4 提取策略

```
优先级 1 — AI 语义分析:
  - 分析 page_interactions 中 interaction_type="dynamic_filter" 的条目
  - 提取 admin_config_source 字段 → 匹配运营后台模块名
  - 自动建议 configures 关系

优先级 2 — 模块名相似度:
  - 用户端模块名与运营后台模块名的模糊匹配
  - 例: "资讯" ↔ "资讯分类配置" → 建议 configures

优先级 3 — 手动:
  - 在版本全景视图中手动建立
```

### 1.10.5 AI 测试用例扩展

`configures` 关系注入测试用例生成 prompt：

```
"该模块的以下功能由运营后台配置控制：
- 资讯分类Tab → 运营后台「资讯分类配置」
- 推荐内容 → 运营后台「推荐位管理」

请生成配置变更影响测试用例：
- 后台修改配置后，用户端对应展示是否同步更新
- 后台禁用某分类后，用户端是否不再展示
- 后台配置为空时，用户端的降级展示"
```

---

## 1.11 🆕 附件内容结构化 v1.3

### 1.11.1 背景

当前设计将说明附件（广告位系统.docx、银钻系统说明.docx 等）作为整体二进制挂载到模块上。但附件内部包含丰富的结构化信息（功能点、规则、流程），提取这些内容能显著提升需求完整度。

### 1.11.2 提取流程

```python
# backend/app/services/knowledge/attachment_extractor.py

class AttachmentContentExtractor:
    """说明附件内容提取器"""

    async def extract(self, attachment_module: RequirementModule) -> AttachmentContent:
        """
        输入: node_type="attachment" 的 RequirementModule（含附件文件 URL）
        
        处理流程:
        1. 下载附件文件（.docx / .pdf / .md）
        2. OCR/文本提取
        3. AI 分析：识别功能点、业务规则、流程图描述
        4. 产出结构化内容

        产出: AttachmentContent {
            summary: str,                # 附件摘要
            functional_points: [         # 提取的功能点
                {name, description, category}
            ],
            business_rules: [            # 业务规则
                {rule, condition, action}
            ],
            related_modules: [str],      # AI 推断的关联模块名
        }
        """
```

### 1.11.3 存储策略

提取的内容**不创建新的 RequirementModule 节点**（避免节点爆炸），而是：
- `summary` → 写入 attachment 节点的 `description` 字段
- `functional_points` → 写入 attachment 节点的 `metadata_json`（JSON 扩展）
- `business_rules` → 存入 `KnowledgeEntity`（entity_type="business_rule"）并关联到模块

### 1.11.4 对导入流程的影响

在 Step 5 (增量提取) 中，对 `node_type="attachment"` 的节点追加：
```
Step 5b (🆕 v1.3): 附件内容结构化
  - 识别 node_type="attachment" 的模块
  - 下载附件文件 → 文本提取 → AI 分析
  - 功能点注入模块描述
  - 业务规则创建 KnowledgeEntity 节点
```

---

## 2. API 设计

### 2.1 发布包 API (`/api/v1/release-bundles`)

```python
# 新建文件: backend/app/api/v1/release_bundle.py

GET    /api/v1/release-bundles
  Query: project_id, status, page, page_size
  Response: PaginatedList[ReleaseBundleOut]
  # 返回发布包列表，按 release_date 倒序

POST   /api/v1/release-bundles
  Body: { name, client_version, admin_version, client_doc_id?, admin_doc_id?,
          release_date?, description?, parent_bundle_id? }  # 🆕 parent_bundle_id
  Response: ReleaseBundleOut
  # 创建发布包。如果提供了 doc_id，自动从文档内容中提取模块树
  # 🆕 如果提供了 parent_bundle_id，自动触发版本 Diff

GET    /api/v1/release-bundles/{id}
  Response: ReleaseBundleDetail (含模块树 + 跨端关联 + 测试用例统计 🆕)
  # 返回完整的版本全景数据

PUT    /api/v1/release-bundles/{id}
DELETE /api/v1/release-bundles/{id}

# === 🆕 v1.1: 版本 Diff ===
POST   /api/v1/release-bundles/{id}/diff
  Body: { parent_bundle_id }
  Response: VersionDiffResult {
    new_modules: [{name, page_count}],
    modified_modules: [{name, parent_module_id, changes: {new_pages, modified_pages, deleted_pages}}],
    deleted_modules: [{name}],
    unchanged_modules: [{name}],  # 跳过的模块
    diff_confidence: float,
  }
  # 触发版本 Diff 分析，返回差异结果供人工审核

POST   /api/v1/release-bundles/{id}/diff/confirm
  Body: { confirmed_modules: [...], overrides: {...} }
  Response: { status: "confirmed", modules_created: N }
  # 人工确认 Diff 结果后，触发增量模块树构建

# 模块关联
POST   /api/v1/release-bundles/{id}/links
  Body: { client_module_id, admin_module_id, notes? }
  Response: ModuleAdminLinkOut

DELETE /api/v1/release-bundles/{id}/links/{link_id}

# AI 辅助
POST   /api/v1/release-bundles/{id}/suggest-links
  Response: [{ client_module_id, admin_module_id, confidence, reason }]
```

### 2.2 模块树 API (`/api/v1/requirement-modules`)

```python
GET    /api/v1/requirement-modules
  Query: document_id, platform, node_type, parent_id, change_type 🆕
  Response: list[RequirementModuleOut]

GET    /api/v1/requirement-modules/{id}/tree
  Query: include_unchanged=false 🆕  # 是否包含未变更页面（从父模块继承）
  Response: ModuleTreeNode  # 递归子节点
  # 🆕 当 include_unchanged=true 且模块有 parent_module_id 时：
  #   合并父版本的 unchanged_pages + 本版本的 new/modified/deleted pages

GET    /api/v1/requirement-modules/{id}/timeline
  Response: ModuleTimeline  # 模块在所有版本中的演化历史
  # 🆕 通过 parent_module_id 链追溯完整演化路径

GET    /api/v1/requirement-modules/{id}/screenshots 🆕
  Response: { screenshots: [{url, page_name, captured_at}] }
  # 获取模块关联的所有截图（跨版本聚合）

# === 🆕 v1.1: 测试用例关联 ===
GET    /api/v1/requirement-modules/{id}/test-cases
  Query: test_case_type (functional/api/automation)
  Response: {
    functional: [{id, name, status, last_run}],
    api: [...],
    automation: [...],
    coverage_rate: float,
  }
  # 获取模块关联的测试用例列表

POST   /api/v1/requirement-modules/{id}/link-test-cases
  Body: { test_case_ids: [int] }
  Response: { linked_count: N }
  # 手动关联用例到模块

POST   /api/v1/requirement-modules/{id}/relate-entity
  Body: { entity_type, entity_id }
  # 将模块节点关联到知识图谱实体

# === 🆕 v1.2: 页面交互跳转 ===
GET    /api/v1/requirement-modules/{id}/interactions
  Response: {
    page_interactions: [...],                       # 该页面的跳转关系
    incoming_navigations: [{from_page, trigger}],   # 哪些页面可以跳转到当前页
    outgoing_navigations: [{to_page, trigger}],     # 当前页可以跳转到哪些页面
  }
  # 获取页面的交互跳转关系（用于版本全景中的页面跳转图）

POST   /api/v1/requirement-modules/{id}/interactions
  Body: { interactions: [{trigger, target_page, target_lanhu_page_id, interaction_type, source_element, description}] }
  Response: { saved: N }
  # 手动编辑/补充页面的交互跳转关系
```

### 2.3 知识图谱层级 API (扩展现有 `/api/v1/knowledge/graph`)

```python
GET    /api/v1/knowledge/graph/hierarchy
  Query: root_type=release_bundle, root_id=X, depth=3, knowledge_domain=project,
         show_test_cases=true 🆕  # 是否在模块/页面下展示关联的测试用例节点
         show_navigations=false 🆕 v1.2  # 是否展示页面间跳转边 (默认隐藏，避免图谱过密)
  Response: HierarchyGraphData {
    nodes: [{ id, name, entity_type, level, children_count, collapsed,
              test_case_summary: { functional: 8, api: 5, automation: 2 } 🆕,
              page_interactions_count: 3 🆕 v1.2 }],
    edges: [{ source, target, relation_type, label 🆕 v1.2 }]
    # 🆕 v1.2: navigates_to 边的 label 取自 trigger 字段 (如 "点击搜索图标")
  }

POST   /api/v1/knowledge/graph/auto-build
  Body: { release_bundle_id }
  Response: {
    entities_created: N, relations_created: M,
    test_cases_linked: K, 🆕  # 自动关联的测试用例数
    navigations_created: L 🆕 v1.2  # 自动建立的页面跳转关系数
  }
  # 从 ReleaseBundle + RequirementModule 自动构建知识图谱节点和关系
  # 实体层级: Project → ReleaseBundle → Platform → Module → Page → TestCase 🆕
  # 自动关系: belongs_to_version, has_platform, has_module, has_page, tested_by 🆕, navigates_to 🆕 v1.2

GET    /api/v1/knowledge/graph/node/{entity_id}/expand
  Query: depth=1, include_test_cases=true 🆕, include_navigations=false 🆕 v1.2
  Response: { nodes: [...], edges: [...] }
  # 🆕 展开模块节点时，自动返回关联的测试用例子节点
  # 🆕 v1.2: 展开页面节点时，可选返回页面间跳转关系

POST   /api/v1/knowledge/graph/evolve
  # 扩展现有 evolve 逻辑，新增：
  # - 检测同模块跨版本的 evolves_from 关系 (通过 parent_module_id 链)
  # - 检测模块名称相似度，建议 links_to_admin 跨端关联
  # - 检测孤立节点（无层级归属的页面/功能点）
  # - 🆕 检测无模块归属的测试用例，建议关联
  # - 🆕 v1.2: 检测 page_interactions 中的 target_page 未匹配到已知页面，建议补充节点
```

### 2.4 Wiki 基线同步 API (扩展现有 `/api/v1/wiki`)

```python
POST   /api/v1/wiki/sync-from-release-bundle
  Body: { release_bundle_id }
  Response: { wiki_raw_source_id, pages_created: N, structure: {...} }
  # 将发布包的模块树同步为 Wiki 目录结构
  # 每个页面创建一个 WikiRawSource → WikiPage 条目
  # 页面内容 = 蓝湖 OCR 文本（已有）+ 模块描述

GET    /api/v1/wiki/release-bundle-structure/{release_bundle_id}
  Response: { wiki_pages: [...], coverage: { total_pages, synced_pages, missing_pages } }
  # 查看发布包在 Wiki 中的映射情况
```

## 3. 图谱关系模型详解

### 3.1 「项目球」层级关系图

```
                        ┌──────────────┐
                        │   Project    │  entity_type: project
                        │   "CamelTv"  │
                        └──────┬───────┘
                               │ belongs_to_version (N条)
                ┌──────────────┼──────────────┐
                │              │              │
         ┌──────┴──────┐ ┌────┴─────┐ ┌──────┴──────┐
         │ReleaseBundle│ │ReleaseB..│ │ReleaseBundle│  entity_type: release_bundle
         │ v2.0.0+后台 │ │v2.5.0    │ │ v3.0.0+后台 │
         └──────┬──────┘ └────┬─────┘ └──────┬──────┘
                │ has_platform │              │
      ┌─────────┼─────────┐    │     ┌────────┼────────┐
      │         │         │    │     │        │        │
   ┌──┴──┐  ┌──┴──┐  ┌──┴──┐ │  ┌──┴──┐ ┌──┴──┐ ┌──┴──┐
   │ APP │  │ PC  │  │ WEB │    │ APP │ │ PC  │ │ WEB │  entity_type: platform
   └──┬──┘  └──┬──┘  └──┬──┘    └──┬──┘ └──┬──┘ └──┬──┘
      │ has_module                  │ has_module
   ┌──┴──┐                    ┌─────┴──────┐
   │资讯  │                    │   直播     │          entity_type: client_module
   └──┬──┘                    └─────┬──────┘
      │ has_page                    │ has_page
   ┌──┼────────┐              ┌────┼──────┐
   │  │        │              │    │      │
┌──┴─┐┌──┴──┐┌──┴──┐    ┌───┴──┐┌┴────┐┌┴────┐
│列表││详情  ││评论  │    │直播间││弹幕  ││礼物  │   entity_type: page
└────┘└─────┘└─────┘    └─────┘└─────┘└─────┘
   │                            │
   │ links_to_admin (虚线)       │
   │                            │
┌──┴──────────┐                 │ (无关联)
│ 资讯分类     │                 │
│ 资讯列表     │                      entity_type: admin_module
│ 评论审核     │
└─────────────┘
   admin_version: v4.0.0
```

### 3.2 版本演化关系

```
Module("资讯", v1.0) ──evolves_from──→ Module("资讯", v2.0) ──evolves_from──→ Module("资讯", v3.0)
       │                                      │                                      │
       ├ Page("资讯列表")                      ├ Page("资讯列表") [修改]               ├ Page("资讯列表")
       └ Page("搜索")                          ├ Page("资讯详情") [新增]               ├ Page("资讯详情")
                                               └ Page("评论")    [新增]               ├ Page("评论")
                                                                                      └ Page("分享")   [新增]

# evolves_from 关系自动建立条件:
# 同名模块 + 不同 ReleaseBundle + 版本号递增
```

### 3.3 实体数量估算与性能策略

| 层级 | 估算数量 (1个项目) | 策略 |
|------|-------------------|------|
| Project | 1 | 常驻 |
| ReleaseBundle | ~30 (历史版本) | 全部加载 |
| Platform | ~90 (3端×30版本) | 全部加载 |
| Module | ~300 (每版本10模块) | 按版本懒加载 |
| Page | ~1500 (每模块5页面) | 按模块懒加载 |
| AdminModule | ~200 | 按关联懒加载 |

**前端策略**：
- 初始加载：只加载 Project + 最新 3 个 ReleaseBundle + 直接子节点
- 展开时懒加载：用户双击节点时请求 `/graph/node/{id}/expand`
- vis-network hierarchical layout，`physics: false`，稳定布局 + 高性能

## 4. 知识中心内容分类重组 🆕 v1.2

### 4.1 现状问题

当前知识中心 Tab 分类存在内容归属混乱：
- **「项目知识」Tab** 目前混入了平台研发内容（Agent Team 开发日志、PRD 文档等）
- 用户期望「项目知识」只存放**体育平台业务知识**（需求文档、模块说明、测试用例等）
- 平台研发相关的内容应归属**「平台研发」Tab**

### 4.2 内容归属定义

| Tab | 定位 | 内容 |
|-----|------|------|
| **项目知识** | 体育平台业务知识 | 需求文档、模块说明、蓝湖原型分析、功能用例、接口用例、业务规则 |
| **平台研发** | 测试平台自身研发 | Agent Team 工作日志、PRD 文档、架构设计、技术决策、开发看板 |
| **检索** | 跨域搜索 | 同时检索项目知识 + 平台研发 + 知识源 |
| **知识源** | 原始数据源 | 蓝湖证据包、Swagger 文档、导入的测试用例文件 |

### 4.3 多业务平台扩展

当前只有一个业务线（体育平台）。未来如果新增业务平台（如直播平台、社区平台），按以下方式扩展：

```
项目知识 (Tab)
  ├── 体育平台 (Project)        ← 当前
  │     ├── 需求文档 / 模块
  │     ├── 功能用例 / 接口用例
  │     └── 业务规则
  ├── 直播平台 (Project)        ← 未来
  │     └── ...
  └── 社区平台 (Project)        ← 未来
        └── ...
```

**实现方式**：在「项目知识」Tab 内增加项目选择器（下拉/侧边栏），按 `project_id` 过滤。当前仅一个项目时默认选中，无需显示选择器。

### 4.4 实施

**不需要代码变更**——这是内容组织层面的调整。需要：

**Step 1 — 存量数据自动分类** 🆕 v1.3:
```python
# 自动分类规则（按来源+内容特征）：
# → knowledge_domain = "platform_development":
#   - 来源为 Agent Team 工作日志
#   - 标题匹配: "Batch *" / "Slice *" / "PRD" / "技术架构" / "Design Spec"
#   - chunk_type = "work_log" | "dev_diary" | "prd_document"
#
# → knowledge_domain = "project_knowledge":
#   - 来源为蓝湖导入 / 需求文档
#   - 标题匹配: "用户端*" / "运营后台*" / "版本*" / "模块*"
#   - chunk_type = "requirement" | "test_case" | "module_doc"
#
# → 无法自动判定的记录 → knowledge_domain 保持不变，输出到"待审核"列表
```

**Step 2 — 人工抽检**:
- 从自动分类结果中每类随机抽取 20 条
- 人工验证分类是否正确
- 准确率 ≥95% → 通过；否则调整规则重新分类

**Step 3 — 回滚方案**:
- 迁移前备份 `knowledge_domain` 字段快照（导出 CSV）
- 如果迁移后发现分类错误 → 从快照恢复

**Step 4 — 前端过滤更新**:
- 「项目知识」Tab: `knowledge_domain=project_knowledge`（排除 `platform_development`）
- 「平台研发」Tab: `knowledge_domain=platform_development`
- 「检索」Tab: 不限

**Step 5 — 增量数据规范**:
- Agent Team 日志入库 (`ingest_platform_knowledge`) → 自动标记 `knowledge_domain=platform_development`
- 体育平台业务知识导入 → 标记 `knowledge_domain=project_knowledge` + `project_id`
- 未来新业务平台 → `knowledge_domain=project_knowledge` + 新 `project_id`

**用户确认**: 经人工检查，现有测试平台「项目知识」内容全部属于平台研发。按照原有分类规则迁移到「平台研发」Tab 即可。

---

## 5. 蓝湖→Wiki 同步基线机制

### 4.1 同步流程

```
LanhuEvidenceJob (OCR完成)
       │
       ▼
Import evidence → RequirementDocument (file_type=lanhu)
       │
       ├──→ KnowledgeSource (RAG 知识库)
       │       └── KnowledgeChunk → KnowledgeVector
       │
       └──→ WikiRawSource (Wiki 基线) — 本批次增强
               │
               ▼
         auto_build_module_tree()  ← 新增：从 OCR 文本 + 页面列表提取层级结构
               │
               ▼
         RequirementModule 树 (平台 → 模块 → 页面)
               │
               ▼
         ReleaseBundle (手动/半自动创建)
               │
               ▼
         sync_to_wiki()  ← 新增：将模块树同步为 Wiki 目录
               │
               ▼
         WikiRawSource (每页面) → WikiIngestJob → WikiPage
```

### 4.2 自动提取模块树

从蓝湖证据包中自动提取层级结构：

```python
# backend/app/services/knowledge/module_extractor.py

async def extract_module_tree(job: LanhuEvidenceJob) -> list[ModuleTreeNode]:
    """
    从蓝湖证据包的页面列表中提取层级结构。
    
    输入：
    - 蓝湖文档 URL (含 folder/page 层级信息)
    - 页面 OCR 文本
    - 页面截图
    
    启发式规则：
    1. 蓝湖 URL 中的 parentId 关系 → 页面归属
    2. 页面名称模式："更新日志" → changelog_entry
    3. 文件夹名称 → 平台/模块分类
       - "APP端"/"客户端" → platform=APP
       - "PC端"/"PC浏览器" → platform=PC
       - "WEB端"/"移动端H5" → platform=WEB
       - "说明附件" → node_type=attachment
    4. 非更新日志页面 → 按文件夹归类为模块/页面
    
    输出：
    - 树形结构，每层标注 platform/node_type
    - AI 辅助：DeepSeek 识别模块边界和页面归属
    """
```

### 4.3 Wiki 目录结构映射

蓝湖结构 → Wiki 目录：

```
蓝湖结构                           Wiki 页面结构
─────────────                      ─────────────
用户原型需求.rp                    
├── 更新日志                       /体育平台/版本历史/
│   ├── v3.0.0 更新内容            /体育平台/版本历史/v3.0.0/
│   ├── v2.5.0 更新内容            /体育平台/版本历史/v2.5.0/
│   └── ...                        
├── 说明附件                       /体育平台/说明附件/
│   ├── 资讯模块PRD.docx           /体育平台/说明附件/资讯模块PRD/
│   └── ...                        
├── APP端                          /体育平台/APP端/
│   ├── 资讯                       /体育平台/APP端/资讯/
│   │   ├── 资讯列表               /体育平台/APP端/资讯/资讯列表/
│   │   └── 资讯详情               /体育平台/APP端/资讯/资讯详情/
│   └── ...                        
├── PC端                           /体育平台/PC端/...
└── WEB端                          /体育平台/WEB端/...

运营后台.rp                        
├── 更新日志                       /体育平台/运营后台/版本历史/
├── 资讯管理                       /体育平台/运营后台/资讯管理/
│   ├── 资讯分类                   /体育平台/运营后台/资讯管理/资讯分类/
│   └── 资讯列表                   /体育平台/运营后台/资讯管理/资讯列表/
└── ...                            
```

## 6. 兼容性保证

### 5.1 不破坏现有功能

- `RequirementDocument` 仅新增 2 个可选字段 (`platform`, `doc_type`)，默认值兼容存量数据
- `KnowledgeSource` 仅新增 1 个可选字段 (`module_id`)，默认 None
- `KnowledgeEntity` / `KnowledgeRelation` 不需要 DDL 变更（entity_type/relation_type 是字符串）
- 所有新模型使用独立的表，不修改现有表结构
- 新 API 使用独立路由前缀 (`/release-bundles`, `/requirement-modules`)

### 5.2 存量数据处理

- 存量 `RequirementDocument` 的 `doc_type` 默认为 `"rp"`（如果是蓝湖链接）
- 存量 `KnowledgeEntity` 的 `entity_type` 保持不变（api/field/requirement/test_case/defect）
- 提供 `/knowledge/graph/auto-build` 接口可对历史数据按需构建层级图谱
- 不强制迁移——旧数据可继续使用扁平图谱视图

### 5.3 Feature Flag

```python
# 新增 feature flag (默认 OFF，渐进启用)
project_sphere_enabled: bool = False   # 版本全景 + 项目球图谱
module_tree_enabled: bool = False      # 模块树提取
wiki_sync_baseline_enabled: bool = False  # Wiki 基线同步
```

## 7. Alembic 迁移计划 (v1.3 修订)

```python
# 新增迁移文件 (3个表 + 6个扩展字段 — v1.3: +page_interactions + global_navigation)

def upgrade():
    # 1. 扩展 requirement_document
    op.add_column('requirement_document', sa.Column('platform', sa.String(50), default=''))
    op.add_column('requirement_document', sa.Column('doc_type', sa.String(20), default='rp'))

    # 2. 扩展 knowledge_source
    op.add_column('knowledge_source', sa.Column('module_id', sa.Integer(), nullable=True))
    op.create_index('ix_knowledge_source_module_id', 'knowledge_source', ['module_id'])

    # 3. 新建 requirement_module (含 v1.1/v1.2 新增字段)
    op.create_table('requirement_module',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('document_id', sa.Integer(), sa.ForeignKey('requirement_document.id'), index=True),
        sa.Column('parent_id', sa.Integer(), nullable=True, index=True),
        sa.Column('node_type', sa.String(20), default='module', index=True),
        sa.Column('name', sa.String(200), default=''),
        sa.Column('description', sa.Text(), default=''),
        sa.Column('platform', sa.String(20), default='', index=True),
        sa.Column('sort_order', sa.Integer(), default=0),
        sa.Column('lanhu_page_id', sa.String(100), default=''),
        sa.Column('change_type', sa.String(20), default='new'),
        # 🆕 v1.1
        sa.Column('parent_module_id', sa.Integer(), nullable=True, index=True),
        sa.Column('source_version', sa.String(50), default=''),
        sa.Column('screenshot_urls', sa.Text(), default='[]'),
        sa.Column('has_visual_only_content', sa.Boolean(), default=False),
        # 🆕 v1.2: 页面交互跳转
        sa.Column('page_interactions', sa.Text(), default='[]'),
        # 时间戳
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # 4. 新建 release_bundle (含 v1.1 + v1.3 新增字段)
    op.create_table('release_bundle',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('project_id', sa.Integer(), index=True),
        sa.Column('name', sa.String(200), default=''),
        sa.Column('client_version', sa.String(50), default='', index=True),
        sa.Column('admin_version', sa.String(50), default=''),
        sa.Column('release_date', sa.DateTime(), nullable=True),
        sa.Column('description', sa.Text(), default=''),
        sa.Column('client_doc_id', sa.Integer(), nullable=True),
        sa.Column('admin_doc_id', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(20), default='draft', index=True),
        sa.Column('metadata_json', sa.Text(), default='{}'),
        # 🆕 v1.1
        sa.Column('parent_bundle_id', sa.Integer(), nullable=True, index=True),
        sa.Column('diff_summary', sa.Text(), default='{}'),
        # 🆕 v1.3: 全局导航
        sa.Column('global_navigation', sa.Text(), default='[]'),
        # 时间戳
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # 5. 新建 module_admin_link
    op.create_table('module_admin_link', ...)

def downgrade():
    # 反向操作（可回滚）
    op.drop_table('module_admin_link')
    op.drop_table('release_bundle')
    op.drop_table('requirement_module')
    op.drop_column('knowledge_source', 'module_id')
    op.drop_column('requirement_document', 'doc_type')
    op.drop_column('requirement_document', 'platform')
```
