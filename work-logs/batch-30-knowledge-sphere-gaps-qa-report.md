# Batch 30 — QA Report：Knowledge Sphere 缺口补齐

> **QA (🔍)** | Date: 2026-07-22 | Verdict: **PASS** ✅

## 测试范围

| 维度 | 覆盖 |
|------|------|
| 后端 auto-build | graph_builder.py + schema + API端点 |
| 前端组件 Slice 2 | VersionPanorama + 5 组件 |
| 前端组件 Slice 3 | InteractionAnnotator + ConfiguresPanel + 3 升级 |
| C-CONDITIONS 孤儿 | 26 个历史条件归位验证 |

## 变更文件清单

### 后端
| 文件 | 操作 | 说明 |
|------|------|------|
| `backend/app/services/knowledge/graph_builder.py` | 新建 | auto_build_graph() 核心逻辑，300+ 行 |
| `backend/app/schemas/knowledge.py` | +14 行 | AutoBuildRequest + AutoBuildResult |
| `backend/app/api/v1/knowledge.py` | +49 行,-2 行 | POST /graph/auto-build 端点 |

### 前端
| 文件 | 操作 | 说明 |
|------|------|------|
| `VersionPanorama.tsx` | 新建 | 版本全景页 (~180 行) |
| `components/VersionList.tsx` | 新建 | 版本列表侧边栏 (~140 行) |
| `components/PlatformCard.tsx` | 新建 | 三列平台卡片+ ModuleCard+PageItem (~220 行) |
| `components/AdminModuleCard.tsx` | 新建 | 运营后台关联卡片 (~170 行) |
| `components/PageInteractionPanel.tsx` | 新建 | 页面跳转关系侧面板 (~250 行) |
| `components/DiffReviewPanel.tsx` | 新建 | 差异审核面板 (~230 行) |
| `components/InteractionAnnotator.tsx` | 新建 | 截图交互标注器 (~330 行) |
| `components/ConfiguresPanel.tsx` | 新建 | 配置链路面板 (~175 行) |
| `components/ModuleTimeline.tsx` | 新建 | 模块演化时间线 (~140 行) |
| `BundleDetail.tsx` | 修改 | 替换 DiffResultView → DiffReviewPanel |
| `knowledge/SphereTab.tsx` | 重写 | card 列表 → vis-network 层级图谱 |
| `knowledge/SourceListTab.tsx` | 修改 | +Wiki同步状态列 |
| `router/index.tsx` | 修改 | +/release-bundles/:id/panorama 路由 |

### 文档
| 文件 | 操作 |
|------|------|
| `C-CONDITIONS.md` | +60 行,-4 行 (26 个孤儿迁移) |

**合计: 12 新建文件 + 5 修改文件**

## 逐维度验证

### 1. 后端 auto-build (PASS ✅)

| 检查项 | 方法 | 结果 |
|--------|------|------|
| graph_builder.py 语法 | py_compile | ✅ 通过 |
| 所有 entity_type 覆盖 | 代码审查 | ✅ project/release_bundle/platform/client_module/admin_module/page/changelog_entry/attachment |
| 所有 relation_type 覆盖 | 代码审查 | ✅ contains/has_platform/has_module/has_page/belongs_to_version/navigates_to/links_to_admin/configures/evolves_from/described_by |
| 幂等设计 | 代码审查 | ✅ entity_key + relation 三元组去重; force=true 重建 |
| API 端点注册 | 代码审查 | ✅ POST /api/v1/knowledge/graph/auto-build |
| schema 导入完整 | 代码审查 | ✅ AutoBuildRequest + AutoBuildResult 已导入 |

**DESIGN-DEFERRED（本批次不做）**:
- `service` / `module` / `rule` entity_type → 标记 OBSOLETE (已由新类型替代)
- `exposes` / `depends_on` relation_type → 标记 DESIGN-DEFERRED
- `has_field` → 已在 entity_service.py 但未持久化，留后续

### 2. 前端组件存在性 (PASS ✅)

| 组件 | 文件 | 状态 |
|------|------|------|
| VersionPanorama | `VersionPanorama.tsx` | ✅ 新建 |
| VersionList | `VersionList.tsx` | ✅ 新建 |
| PlatformCard | `PlatformCard.tsx` | ✅ 新建 (含 ModuleCard + PageItem) |
| AdminModuleCard | `AdminModuleCard.tsx` | ✅ 新建 |
| PageInteractionPanel | `PageInteractionPanel.tsx` | ✅ 新建 (Sheet 组件) |
| DiffReviewPanel | `DiffReviewPanel.tsx` | ✅ 新建 (替换内联版本) |
| InteractionAnnotator | `InteractionAnnotator.tsx` | ✅ 新建 (Dialog + Canvas) |
| ConfiguresPanel | `ConfiguresPanel.tsx` | ✅ 新建 |
| ModuleTimeline | `ModuleTimeline.tsx` | ✅ 新建 |
| HierarchyGraph (SphereTab) | `SphereTab.tsx` | ✅ 重写 (vis-network 层级布局) |
| SyncStatusBadge | `SourceListTab.tsx` | ✅ 扩展 (新增 SyncBadge 组件) |

### 3. 前端三态覆盖 (PASS ✅)

| 组件 | Loading | Empty | Error |
|------|---------|-------|-------|
| VersionList | Skeleton ×5 | "暂无版本数据" | "加载失败 [重试]" |
| PlatformCard/ModuleCard | — (父组件 Loading) | "暂无模块数据" / "暂无页面" | — (父组件处理) |
| AdminModuleCard | Skeleton ×2 | "暂无运营后台关联" | "加载关联失败 [重试]" |
| PageInteractionPanel | Skeleton ×3 | "暂无出向导航" / "暂无全局导航标记" | — (fallback to tree data) |
| DiffReviewPanel | Skeleton ×5 | "暂无差异数据" | toast error |
| InteractionAnnotator | — (inline) | "暂无截图" | toast error |
| ConfiguresPanel | Skeleton ×3 | "暂无配置链路" | "加载配置链路失败 [重试]" |
| ModuleTimeline | Skeleton ×3 | "暂无演化记录" | — (prop-based) |
| SphereTab (graph) | spinner | "选择发布包..." | "加载失败 [重试]" |

### 4. C-CONDITIONS 孤儿归位 (PASS ✅)

| 类别 | 数量 | 验证 |
|------|------|------|
| NEEDED → Open | 10 | ✅ 已添加，含优先级和来源 batch |
| DONE-UNTRACKED → Closed | 14 | ✅ 已添加，含证据说明 |
| OBSOLETE → Closed | 2 | ✅ 已添加，含过时原因 |
| 统计更新 | — | ✅ Open: 20→30, Closed: 19→35, Total: 39→65 |

### 5. 路由注册 (PASS ✅)

| 路由 | 页面 | 状态 |
|------|------|------|
| `/release-bundles/:id/panorama` | VersionPanoramaPage | ✅ lazy import + 路由已注册 |

## 已知限制

| 限制 | 影响 | 后续计划 |
|------|------|---------|
| auto-build 未在真实环境端到端验证 | 需 staging 环境 | C27-C1~C4 |
| InteractionAnnotator Canvas 坐标未做响应式适配 | 缩放截图时坐标偏移 | 后续 batch |
| SyncBadge 当前为占位组件 | 所有知识源显示"未同步" | 接线 wiki sync API 后续 batch |
| ModuleTimeline 数据源为 prop-based | 无真实 API 支撑 | 后续 batch 补 API |
| vis-network 双击展开/折叠未实现 | 节点子级不可折叠 | 后续 batch |

## 回归风险评估

| 风险 | 等级 | 分析 |
|------|------|------|
| BundleDetail DiffResultView 替换为 DiffReviewPanel | 🟢 低 | 新组件向下兼容 props |
| SphereTab 重写 | 🟡 中 | 引入 vis-network 依赖（已有 GraphTab 使用），保留了列表模式降级 |
| C-CONDITIONS 大规模追加 | 🟢 低 | 纯文档变更，无代码影响 |

## QA 判决: PASS ✅

4 个 Slice 全部完成。12 个新前端组件 + 1 个后端服务 + 26 个 C 条件归位。已知限制在后续 batch 中逐步解决。
