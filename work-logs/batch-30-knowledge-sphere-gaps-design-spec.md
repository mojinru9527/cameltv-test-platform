# Batch 30 — Design Spec：Knowledge Sphere 缺口补齐

> **Design (🎨)** | Date: 2026-07-22 | Status: 草稿

## 0. 技术体系确认

- **后端**: FastAPI + SQLAlchemy 2.0 + Pydantic v2，延续现有 `entity_service.py` 模式
- **前端**: shadcn/ui + Radix + Tailwind + CVA，延续现有组件模式
- **图谱**: vis-network (已集成在 GraphTab)，SphereTab 复用
- **Token**: Tailwind 语义类（`bg-muted`, `text-muted-foreground`, `border`, `variant`）

---

## Part A: 后端 auto-build

### A1. API 端点设计

```
POST /api/v1/knowledge/graph/auto-build
```

**Request**:
```json
{
  "release_bundle_id": 1
}
```

**Response (200)**:
```json
{
  "created_entities": 42,
  "created_relations": 38,
  "skipped_entities": 0,
  "skipped_relations": 0,
  "message": "Graph built successfully for release bundle v14.1.0"
}
```

**Response (409 - already built)**:
```json
{
  "created_entities": 0,
  "created_relations": 0,
  "skipped_entities": 42,
  "skipped_relations": 38,
  "message": "Graph already built for this release bundle. Use force=true to rebuild."
}
```

### A2. graph_builder 服务架构

```
graph_builder.py
├── auto_build_graph(db, release_bundle_id, force=False) → AutoBuildResult
│   ├── _ensure_project_entity(db, project) → KnowledgeEntity
│   ├── _build_bundle_entities(db, bundle) → entity_map
│   │   ├── release_bundle entity (entity_key: "release_bundle:{name}:{version}")
│   │   ├── platform entities (entity_key: "platform:{name}:{version}:{platform}")
│   │   ├── client_module entities (entity_key: "client_module:{name}:{version}:{platform}:{module}")
│   │   ├── admin_module entities (entity_key: "admin_module:{name}:{version}:{module}")
│   │   └── page entities (entity_key: "page:{name}:{version}:{platform}:{module}:{page}")
│   └── _build_relations(db, entity_map, bundle) → relation_count
│       ├── belongs_to_version: bundle → release_bundle
│       ├── has_platform: bundle → platform
│       ├── has_module: platform → client_module
│       ├── has_page: client_module → page
│       ├── links_to_admin: client_module → admin_module (via ModuleAdminLink)
│       ├── tested_by: page → test_case (via test_case_linker)
│       ├── navigates_to: page → page (via page_interactions)
│       ├── configures: client_module → admin_module (via configures_linker)
│       └── described_by: entity → attachment (via attachment_extractor)
```

### A3. 幂等策略

- 按 `(entity_type, entity_key, project_id)` 三元组查重
- 按 `(from_entity_id, relation_type, to_entity_id)` 三元组查重
- `force=true` 时删除该 bundle 所有现有实体和关系后重建

### A4. entity_type / relation_type 完整清单

**entity_type（全部接线目标）**:
| entity_type | 接线位置 | entity_key 格式 |
|-------------|---------|-----------------|
| project | graph_builder._ensure_project_entity | `project:{name}` |
| release_bundle | graph_builder._build_bundle_entities | `release_bundle:{name}:{version}` |
| platform | graph_builder._build_bundle_entities | `platform:{name}:{version}:{platform}` |
| client_module | graph_builder._build_bundle_entities | `client_module:{name}:{version}:{platform}:{module}` |
| admin_module | graph_builder._build_bundle_entities | `admin_module:{name}:{version}:{module}` |
| page | graph_builder._build_bundle_entities | `page:{name}:{version}:{platform}:{module}:{page_name}` |
| test_case | 已有 (entity_service.py) | 已有 |
| api | 已有 (entity_service.py) | 已有 |
| field | 已有 (entity_service.py) | 已有 |
| requirement | 已有 (entity_service.py) | 已有 |
| defect | 已有 (entity_service.py) | 已有 |
| business_rule | 已有 (attachment_extractor.py) | 已有 |
| changelog_entry | graph_builder（从 VersionDiffer 输出取） | `changelog_entry:{bundle_key}:{page}:{version}` |
| attachment | attachment_extractor 扩展 | `attachment:{source_type}:{source_id}:{filename}` |
| service | 标记 OBSOLETE（设计文档遗留，由 module 替代） | — |
| module | 标记 OBSOLETE（拆分为 client_module + admin_module） | — |
| rule | 标记 OBSOLETE（由 business_rule 替代） | — |
| iteration | graph_builder（关联 KnowledgeIteration） | `iteration:{iteration_name}` |

**relation_type（全部接线目标）**:
| relation_type | 接线位置 |
|---------------|---------|
| belongs_to_version | graph_builder: bundle → release_bundle |
| has_platform | graph_builder: bundle → platform |
| has_module | graph_builder: platform → client_module |
| has_page | graph_builder: client_module → page |
| links_to_admin | graph_builder: client_module → admin_module |
| tested_by | graph_builder / test_case_linker |
| navigates_to | graph_builder / navigates_to_extractor |
| configures | 已有 (configures_linker.py) |
| described_by | 已有 (attachment_extractor.py) |
| contains | 已有 (entity_service.py) |
| executed_by | 已有 (entity_service.py) |
| affects | 已有 (entity_service.py) |
| covers | 已有 (entity_service.py) |
| generated_from | 已有 (entity_service.py) |
| evolves_from | graph_builder: module@v1 → module@v2（跨版本同模块） |
| has_field | 已有 entity_service.py 但不持久化 → 扩展持久化 |
| exposes | API → field 关系 → 标记 DESIGN-DEFERRED（field 已通过 contains 关联） |
| depends_on | 跨模块依赖 → 标记 DESIGN-DEFERRED（需 AI 分析） |

**标记为 DESIGN-DEFERRED 的类型（本 batch 不做）**:
- `service` entity_type → 由 module 体系替代
- `module` entity_type → 拆分为 client_module/admin_module
- `rule` entity_type → 由 business_rule 替代
- `exposes` → field 已通过 `contains` 关联
- `depends_on` → 跨模块依赖需 AI 分析，后续 batch

---

## Part B: 前端组件规格

### B1. VersionPanorama 页面

**路由**: `/release-bundles/:id/panorama`

**布局**（≥1280px）:
```
┌──────────┬──────────────────────────────────────────┐
│ Version  │  📱 APP        │  🖥️ PC       │  🌐 WEB    │
│ List     │  ┌──────────┐  │  ┌──────────┐ │  ┌──────┐  │
│ (w-64)   │  │ Module A │  │  │ Module X │ │  │Mod M │  │
│          │  │ - Page 1 │  │  │ - Page α │ │  │- Pg 1 │  │
│ v14.1.0● │  │ - Page 2 │  │  │ - Page β │ │  │- Pg 2 │  │
│ v14.0.0  │  │ ──────── │  │  └──────────┘ │  └──────┘  │
│ v13.9.0  │  │ Module B │  │                │           │
│          │  └──────────┘  │                │           │
│          ├────────────────┴────────────────┴───────────┤
│          │  🔗 运营后台关联 (Admin Modules)             │
│          │  ┌──────────────────────────────────────┐   │
│          │  │ 用户管理 → 运营后台·用户模块          │   │
│          │  │ 赛事配置 → 运营后台·赛事管理          │   │
│          │  └──────────────────────────────────────┘   │
└──────────┴──────────────────────────────────────────────┘
```

**响应式断点**:
| 断点 | 布局 |
|------|------|
| ≥1280px | 三列（APP/PC/WEB） |
| 768-1279px | 两列堆叠 |
| <768px | 单列 + 平台 Tab 切换 |

**三态**:
- Loading: 3 列 Skeleton（每列 3 个 Card Skeleton）
- Empty: 居中插画 + "暂无版本数据" + "导入模块树" 按钮
- Error: 红色提示 + "加载失败" + 重试按钮

### B2. PlatformCard（含 ModuleCard / PageItem）

**组件树**: `PlatformCard > ModuleCard[] > PageItem[]`

**PlatformCard**:
```jsx
<Card className="flex-1 min-w-0">
  <CardHeader className="pb-2">
    <div className="flex items-center gap-2">
      {PLATFORM_ICONS[platform]} {/* 📱/🖥️/🌐 */}
      <CardTitle className="text-base">{PLATFORM_LABELS[platform]}</CardTitle>
      <Badge variant="secondary">{modules.length} 模块</Badge>
    </div>
  </CardHeader>
  <CardContent>
    {modules.map(m => <ModuleCard key={m.id} module={m} />)}
  </CardContent>
</Card>
```

**ModuleCard**:
```jsx
<Collapsible defaultOpen>
  <CollapsibleTrigger className="flex items-center w-full p-2 hover:bg-muted rounded-md">
    <ChevronRight className="h-4 w-4 transition-transform duration-200
      [[data-state=open]_&]:rotate-90" />
    <span className="font-medium text-sm ml-2">{module.name}</span>
    <Badge variant="outline" className="ml-auto">{module.pages.length} 页</Badge>
  </CollapsibleTrigger>
  <CollapsibleContent>
    {module.pages.map(p => <PageItem key={p.id} page={p} />)}
  </CollapsibleContent>
</Collapsible>
```

**PageItem**:
```jsx
<div className="flex items-center pl-8 pr-2 py-1.5 hover:bg-accent rounded-sm 
     cursor-pointer text-sm"
     onClick={() => openInteractionPanel(page)}>
  <span className="truncate flex-1">{page.name}</span>
  {/* 跳转关系徽章 */}
  {outgoing > 0 && <Badge variant="secondary" className="ml-1 text-xs">
    →{outgoing}</Badge>}
  {incoming > 0 && <Badge variant="secondary" className="ml-1 text-xs">
    ←{incoming}</Badge>}
  {/* dynamic_filter 紫色标记 */}
  {hasDynamicFilter && <Badge className="ml-1 text-xs bg-purple-100 text-purple-700 
     dark:bg-purple-900 dark:text-purple-300">动态筛选</Badge>}
</div>
```

**颜色映射**（复用设计 spec §2.1）:
| 实体类型 | Tailwind 色 |
|----------|------------|
| client_module | `bg-blue-100 text-blue-700` |
| admin_module | `bg-orange-100 text-orange-700` |
| page | `bg-green-100 text-green-700` |
| global_nav | `bg-purple-100 text-purple-700` |

### B3. AdminModuleCard

```
┌──────────────────────────────────────────┐
│  🔗 运营后台关联              [展开/折叠]  │
├──────────────────────────────────────────┤
│  📱 用户模块  ──configures──▶  🖥️ 用户管理 │
│     置信度 0.92                          │
│  📱 赛事中心  ──configures──▶  🖥️ 赛事配置 │
│     置信度 0.85              [✕ 删除]    │
│  ─────────────────────────────────────── │
│  [+ 手动关联]  [🤖 AI 推荐]               │
└──────────────────────────────────────────┘
```

### B4. PageInteractionPanel

**组件**: shadcn/ui `Sheet` (side="right", className="w-[400px] sm:w-[540px]")

```
┌─ PageInteractionPanel ─────────────────────┐
│  首页 (📱 APP)                      [✕ 关闭] │
├─────────────────────────────────────────────┤
│  📤 出向导航 (3)                            │
│  ┌──────────────────────────────────────┐   │
│  │ 赛事列表 → 赛事详情  [tab_switch]     │   │
│  │ 首页 → 搜索页      [modal]           │   │
│  │ 筛选栏 → 赛事列表  [dynamic_filter]🟣 │   │
│  └──────────────────────────────────────┘   │
│                                             │
│  📥 入向导航 (2)                            │
│  ┌──────────────────────────────────────┐   │
│  │ 登录页 → 首页      [navigation]       │   │
│  │ 注册页 → 首页      [navigation]       │   │
│  └──────────────────────────────────────┘   │
│                                             │
│  🌐 全局导航 (1)                            │
│  ┌──────────────────────────────────────┐   │
│  │ 首页 [底部Tab·默认]  [global_navigation]│  │
│  └──────────────────────────────────────┘   │
│                                             │
│  [🎯 标注截图交互]                           │
└─────────────────────────────────────────────┘
```

### B5. DiffReviewPanel

**四区域布局**:
```
┌─ DiffReviewPanel ──────────────────────────┐
│  [新增 3] [修改 7] [删除 1] [未变更 42] 标签 │
│  ───────────────────────────────────────── │
│  ▼ 用户模块 (APP)        [✓ 确认] [✏️ 修正] │
│    ├─ + 个人中心页面        [新增]          │
│    ├─ ~ 首页               [修改: 标题变更] │
│    └─ - 旧版充值页          [删除]          │
│  ───────────────────────────────────────── │
│  ▼ 赛事模块 (APP)                          │
│    ├─ ~ 赛事列表            [修改: 筛选项+] │
│    └─ + 直播详情页          [新增]          │
│  ───────────────────────────────────────── │
│  [确认全部] [导出报告] [确认并继续]          │
└────────────────────────────────────────────┘
```

**模块行颜色**:
- 有新增: `border-l-2 border-l-green-500`
- 有修改: `border-l-2 border-l-yellow-500`
- 有删除: `border-l-2 border-l-red-500`
- 仅未变更: `border-l-2 border-l-muted`

### B6. InteractionAnnotator

**全屏 Dialog**:
```
┌─ InteractionAnnotator ─────────────────────────────────────┐
│  📸 页面交互标注 — 首页 (APP)                        [✕]    │
├──────────────────────────┬─────────────────────────────────┤
│                          │  标注列表 (3)                    │
│   ┌──────────────────┐   │  ┌───────────────────────────┐  │
│   │                  │   │  │ 区域1: 顶部Banner         │  │
│   │   [截图预览]     │   │  │ → 赛事详情 [tab_switch]   │  │
│   │                  │   │  │ [✏️] [🗑️]                  │  │
│   │   ┌──────┐       │   │  ├───────────────────────────┤  │
│   │   │热区 1│       │   │  │ 区域2: 搜索按钮           │  │
│   │   └──────┘       │   │  │ → 搜索页 [modal]         │  │
│   │                  │   │  │ [✏️] [🗑️]                  │  │
│   │   ┌────┐         │   │  ├───────────────────────────┤  │
│   │   │热区2│        │   │  │ 区域3: 筛选栏             │  │
│   │   └────┘         │   │  │ → 赛事列表 [dynamic_filter]│  │
│   │                  │   │  │ 🔗 运营后台·赛事配置      │  │
│   └──────────────────┘   │  │ [✏️] [🗑️]                  │  │
│                          │  └───────────────────────────┘  │
│                          │  [+ 添加标注区域]               │
│                          │  [保存] [取消]                  │
├──────────────────────────┴─────────────────────────────────┤
│  ☐ 全局导航: 将此页面标记为全局导航入口                      │
└────────────────────────────────────────────────────────────┘
```

**技术实现**: HTML Canvas overlay on `<img>`，mousedown/mousemove/mouseup 事件绘制矩形。坐标转换：canvas 坐标 / 图片自然尺寸比例。

### B7. ConfiguresPanel

```
┌─ ConfiguresPanel ──────────────────────────┐
│  配置链路 (4)               [🤖 AI 推荐]     │
│  ───────────────────────────────────────── │
│  ┌──────────────────────────────────────┐  │
│  │ 📱 用户模块  ──configures──▶  🖥️ 用户管理 │
│  │    置信度 0.92    [✓] [✕]             │  │
│  ├──────────────────────────────────────┤  │
│  │ 📱 赛事中心  ──configures──▶  🖥️ 赛事配置 │
│  │    置信度 0.85    [✓] [✕]             │  │
│  ├──────────────────────────────────────┤  │
│  │ 📱 充值模块  ──configures──▶  🖥️ 财务管理 │
│  │    置信度 0.71    [✓] [✕]             │  │
│  └──────────────────────────────────────┘  │
│  [批量确认] [+ 手动创建链接]                │
└────────────────────────────────────────────┘
```

### B8. HierarchyGraph（SphereTab 重写）

**vis-network 配置**（复用 GraphTab 模式）:
```javascript
const options = {
  layout: {
    hierarchical: {
      enabled: true,
      direction: 'UD',        // 上→下
      sortMethod: 'directed',
      levelSeparation: 120,
      nodeSpacing: 180,
    },
  },
  physics: { enabled: false }, // 层级布局禁用物理
  edges: {
    arrows: { to: { enabled: true, scaleFactor: 0.8 } },
    smooth: { type: 'cubicBezier' },
  },
  interaction: {
    hover: true,
    tooltipDelay: 200,
    navigationButtons: true,
    keyboard: true,
  },
}
```

**节点着色**（复用设计 spec §2.1）:
| entity_type | color |
|-------------|-------|
| release_bundle | `#6366F1` indigo |
| platform | `#8B5CF6` violet |
| client_module | `#3B82F6` blue |
| admin_module | `#F97316` orange |
| page | `#22C55E` green |
| test_case | `#EF4444` red |
| business_rule | `#EAB308` yellow |
| api | `#06B6D4` cyan |

**边着色**（复用设计 spec §2.3）:
| relation_type | color | dashes |
|---------------|-------|--------|
| belongs_to_version / has_platform / has_module / has_page | `#94A3B8` gray | false |
| navigates_to | `#3B82F6` blue | true |
| configures / links_to_admin | `#F97316` orange | false |
| tested_by | `#22C55E` green | true |

**工具栏**:
```
[层级图] [力导向图]  边筛选: ☑层级 ☑跳转 ☑配置 ☑用例   节点大小: [置信度] [出度]
```

### B9. ModuleTimeline

```
┌─ ModuleTimeline: 用户模块 ──────────────────┐
│  ● v14.1.0 (当前)                           │
│  │  ┌──────────────────────────────────┐    │
│  │  │ + 个人中心 (新增)                  │    │
│  │  │ ~ 首页 (修改: 标题改为"推荐")      │    │
│  └──┤ - 旧充值页 (删除)                  │    │
│     │                                   │    │
│  ● v14.0.0                              │    │
│  │  ┌──────────────────────────────────┐    │
│  │  │ + 直播详情页 (新增)               │    │
│  └──┤ ~ 首页 (修改: 增加Banner)         │    │
│     │                                   │    │
│  ● v13.9.0                              │    │
│     └── 本模块首次出现于此版本            │    │
└─────────────────────────────────────────┘
```

### B10. SyncStatusBadge（SourceListTab 扩展）

添加到 `SourceListTab.tsx` 表格的新列：

```jsx
// 列定义
{ key: 'sync_status', label: 'Wiki同步', render: (row) => <SyncBadge sourceId={row.id} /> }

// SyncBadge 组件
function SyncBadge({ sourceId }: { sourceId: number }) {
  // fetch GET /wiki/sync/bundle/{bundleId}/coverage
  // coverage >= 90% → synced (green)
  // coverage >= 50% → partial (yellow)
  // coverage > 0     → unsynced (gray)
  // error            → failed (red)
}
```

**四态映射**:
| 状态 | Badge | Tooltip |
|------|-------|---------|
| synced | `<Badge className="bg-green-100 text-green-700">已同步</Badge>` | 覆盖率: 95% (19/20) |
| partial | `<Badge className="bg-yellow-100 text-yellow-700">部分同步</Badge>` | 覆盖率: 60% (12/20) |
| unsynced | `<Badge variant="outline">未同步</Badge>` | 未关联 Wiki |
| failed | `<Badge className="bg-red-100 text-red-700">同步失败</Badge>` | 上次同步失败: 网络错误 |

---

## C. 已有组件复用

| 设计 spec 组件 | 现有实现 | 本 batch 动作 |
|---------------|---------|--------------|
| VersionList | 无 | **新建** → VersionList.tsx |
| PlatformCard | 无 | **新建** → PlatformCard.tsx |
| ModuleCard | ModuleTreeView.TreeNode (部分) | **新建** → 内嵌 PlatformCard |
| PageItem | ModuleTreeView.TreeNode (部分) | **新建** → 内嵌 ModuleCard |
| AdminModuleCard | 无 | **新建** |
| DiffReviewPanel | BundleDetail.DiffResultView (简化版) | **替换** → DiffReviewPanel.tsx |
| PageInteractionPanel | ModuleTreeView.InteractionPill (内联) | **新建** → PageInteractionPanel.tsx (独立 Sheet) |
| InteractionAnnotator | 无 | **新建** |
| ConfiguresPanel | 无 | **新建** |
| HierarchyGraph | SphereTab (card 列表) | **重写** → vis-network |
| ModuleTimeline | VersionChainTimeline (bundle 级) | **新建** → ModuleTimeline.tsx |
| SyncStatusBadge | 无 | **扩展** → SourceListTab 加列 |
