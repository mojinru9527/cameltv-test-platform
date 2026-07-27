# Batch 30 — PM Plan：Knowledge Sphere 缺口补齐 + C-CONDITIONS 孤儿清理

> **PM (🟨)** | Date: 2026-07-22

## 规格摘要

**原始需求**: PRD batch-30-knowledge-sphere-gaps-prd-summary.md
- 后端：实现 auto-build 端点，接线 10 entity_type + 10 relation_type
- 前端：实现 9 个缺失设计组件 + 1 个小增强
- C-CONDITIONS：26 个孤儿条件归位

**目标时间**: 1 个 batch 内完成全部三个维度

---

## 开发任务

### Slice 1: 后端 auto-build + entity/relation 接线

#### [ ] Task 1.1: 创建 graph_builder service
**描述**: 新建 `backend/app/services/knowledge/graph_builder.py`，实现 `auto_build_graph(release_bundle_id)` 核心逻辑。
**验收标准**:
- 从 ReleaseBundle → RequirementModule tree 出发，构建层级实体和关系
- 实体按 entity_key 去重（幂等）
- 关系按 (from, type, to) 去重（幂等）
- entity_type: `release_bundle`, `platform`, `client_module`, `admin_module`, `page`
- relation_type: `belongs_to_version`, `has_platform`, `has_module`, `has_page`, `tested_by`, `navigates_to`, `configures`, `links_to_admin`
**涉及文件**:
- `backend/app/services/knowledge/graph_builder.py` — 新建
- `backend/app/services/knowledge/__init__.py` — 导出

#### [ ] Task 1.2: 注册 auto-build API 端点
**描述**: 在 knowledge 路由中注册 `POST /api/v1/knowledge/graph/auto-build`。
**验收标准**:
- 接受 `{"release_bundle_id": int}` 入参
- 调用 graph_builder.auto_build_graph()
- 返回 `{created_entities: N, created_relations: N, message: "..."}`
- 幂等：重复调用同 release_bundle_id 返回 "already built"
**涉及文件**:
- `backend/app/api/v1/knowledge.py` — 添加路由
- `backend/app/schemas/knowledge.py` — 添加 `AutoBuildRequest` / `AutoBuildResult` schema

#### [ ] Task 1.3: 补充缺失的 entity_type/relation_type 常量
**描述**: 在 graph_builder 和现有 service 中补充设计文档定义但未使用的类型。
**验收标准**:
- `project` entity_type：在 auto_build 中创建/确保存在
- `service` entity_type：如无需可标记 OBSOLETE
- `module` entity_type：映射到 `client_module`/`admin_module`
- `rule` entity_type：如无需可标记 OBSOLETE
- `iteration` entity_type：关联到 KnowledgeIteration
- `changelog_entry` entity_type：关联到 VersionDiffer 输出
- `attachment` entity_type：在 attachment_extractor 中创建
- relation_type: `has_field`, `exposes`, `depends_on`, `evolves_from`, `links_to_admin` 在 auto_build 阶段创建
**涉及文件**:
- `backend/app/services/knowledge/graph_builder.py`
- `backend/app/services/knowledge/entity_service.py` — 可能需扩展

### Slice 2: 前端组件 (1–5)

#### [ ] Task 2.1: VersionPanorama 页面 + VersionList
**描述**: 新建 `/release-bundles/:id/panorama` 路由页面，左侧版本列表、右侧三列平台卡片。
**验收标准**:
- 三态：Loading (Skeleton) / Empty ("暂无版本数据") / Error ("加载失败 [重试]")
- 左侧 w-64 版本列表，点击切换版本加载对应模块树
- 右侧三列 flex-1 布局 (APP | PC | WEB)
- 响应式：≥1280px 三列，768-1279px 两列堆叠，<768px 单列
**涉及文件**:
- `frontend/src/pages/release-bundles/VersionPanorama.tsx` — 新建
- `frontend/src/pages/release-bundles/components/VersionList.tsx` — 新建
- `frontend/src/router/index.tsx` — 添加路由

#### [ ] Task 2.2: PlatformCard / ModuleCard / PageItem
**描述**: 实现三列平台卡片内的可折叠模块卡片和页面项。
**验收标准**:
- 模块卡片可折叠，header 显示模块名 + 页数
- 页面项显示名称 + 跳转关系徽章（出向/入向计数）
- `dynamic_filter` 类型交互显示紫色标记
- 页面项点击触发 PageInteractionPanel
**涉及文件**:
- `frontend/src/pages/release-bundles/components/PlatformCard.tsx` — 新建

#### [ ] Task 2.3: AdminModuleCard
**描述**: 三列布局下方展示运营后台模块关联。
**验收标准**:
- 展开/折叠区域
- 显示 client_module → admin_module configures 链接
- 支持手动创建/删除关联
**涉及文件**:
- `frontend/src/pages/release-bundles/components/AdminModuleCard.tsx` — 新建

#### [ ] Task 2.4: PageInteractionPanel
**描述**: 侧边滑出面板，展示页面跳转关系。
**验收标准**:
- 使用 shadcn/ui Sheet 组件
- 三个区域：出向导航（来源 → 目标 + 触发描述）、入向导航（哪些页面跳转到此页）、全局导航
- dynamic_filter 类型紫色徽章
- "标注截图交互" 按钮跳转 InteractionAnnotator
**涉及文件**:
- `frontend/src/pages/release-bundles/components/PageInteractionPanel.tsx` — 新建
- `frontend/src/pages/release-bundles/components/ModuleTreeView.tsx` — 添加点击处理

#### [ ] Task 2.5: DiffReviewPanel（替换 BundleDetail DiffResultView）
**描述**: 替换 `BundleDetail.tsx` 中的内联 `DiffResultView` 为独立组件。
**验收标准**:
- 四区域：新增/修改/删除/未变更
- 每个模块可展开查看页面级 diff
- 逐模块确认/修正/拒绝按钮
- "确认全部" "导出报告" 操作栏
**涉及文件**:
- `frontend/src/pages/release-bundles/components/DiffReviewPanel.tsx` — 新建
- `frontend/src/pages/release-bundles/BundleDetail.tsx` — 替换引用

### Slice 3: 前端组件 (6–9 + SyncStatusBadge)

#### [ ] Task 3.1: InteractionAnnotator
**描述**: 全屏截图标注模式，在截图上画矩形热区关联目标页面。
**验收标准**:
- 两列布局：截图画布（左）+ 标注列表（右）
- 鼠标拖拽画矩形框
- 完成矩形后弹出目标页面选择器 + 交互类型选择器
- "标记为全局导航" 复选框
- 保存写入 `page_interactions` JSON
**涉及文件**:
- `frontend/src/pages/release-bundles/components/InteractionAnnotator.tsx` — 新建

#### [ ] Task 3.2: ConfiguresPanel
**描述**: 展示 client↔admin 配置链路关系面板。
**验收标准**:
- 列表展示 configures 链接（client_module / arrow / admin_module / confidence）
- "AI 推荐" 按钮触发 suggestConfigures
- 逐条确认/拒绝 → "批量确认"
- 支持手动创建链接
**涉及文件**:
- `frontend/src/pages/release-bundles/components/ConfiguresPanel.tsx` — 新建
- `frontend/src/pages/release-bundles/BundleDetail.tsx` — 添加 Tab

#### [ ] Task 3.3: HierarchyGraph（SphereTab 重写）
**描述**: 用 vis-network 层级布局替代 SphereTab 的卡片列表。
**验收标准**:
- `layout.hierarchical.enabled: true, direction: 'UD'`
- 节点按 entity_type 着色（复用设计 spec 色板）
- 边按 relation_type 着色
- 边类型筛选 toggle（层级边/页面跳转/configures/测试用例）
- 右侧图例 + 详情面板
- 双击节点展开/折叠子节点
**涉及文件**:
- `frontend/src/pages/knowledge/components/SphereTab.tsx` — 重写

#### [ ] Task 3.4: ModuleTimeline
**描述**: 模块级演化时间线，展示模块跨版本变更。
**验收标准**:
- 垂直时间线，复用 VersionChainTimeline 布局
- 每个版本节点显示该模块的页面变更（新增/修改/删除）
- 颜色编码：绿（新增）、黄（修改）、红（删除）、灰（未变更）
**涉及文件**:
- `frontend/src/pages/release-bundles/components/ModuleTimeline.tsx` — 新建

#### [ ] Task 3.5: SyncStatusBadge
**描述**: 在 SourceListTab 表格中新增 Wiki 同步状态列。
**验收标准**:
- 四态：已同步（绿勾）、部分同步（黄刷新）、未同步（灰）、失败（红叉）
- hover tooltip 显示覆盖率详情
**涉及文件**:
- `frontend/src/pages/knowledge/components/SourceListTab.tsx` — 添加列

### Slice 4: C-CONDITIONS 孤儿归位

#### [ ] Task 4.1: 迁移 26 个孤儿条件到 C-CONDITIONS.md
**描述**: 将侦察报告中的 26 个孤儿条件写入 C-CONDITIONS.md。
**验收标准**:
- 14 个 DONE-UNTRACKED → Closed 区，注明证据（commit/文件:行号）
- 10 个 NEEDED → Open 区，标优先级和来源 batch
- 2 个 OBSOLETE → Closed 区，注明过时原因
- 统计数字更新：Open/Closed/Total
**涉及文件**:
- `C-CONDITIONS.md` — 追加记录 + 更新统计

---

## 质量要求

- [ ] 响应式（Desktop + Tablet + Mobile）
- [ ] 前端 0 TS 错误 + 0 ESLint 错误
- [ ] 后端 0 mypy 错误（新增代码）
- [ ] 加载/空/错误三态覆盖所有新组件
- [ ] 无 console 报错/告警
