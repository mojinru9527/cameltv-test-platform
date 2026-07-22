# Batch 30 — PRD Summary：Knowledge Sphere 缺口补齐 + C-CONDITIONS 孤儿清理

> **Product (🟦)** | Date: 2026-07-22 | Status: Draft

## 1. 问题陈述

Batch 27 Knowledge Sphere (知识球) 代码已合入 PR #52，但走查发现三个维度的缺口：

### 1.1 后端：图谱实体/关系未接线

设计文档 `batch-27-knowledge-sphere-dev-design.md` 定义了 19 种 entity_type 和 18 种 relation_type，但实际代码中仅接线了 ~50%。**10 个 entity_type + 10 个 relation_type 在设计文档中明确定义但在代码中不存在**。根因是设计文档中的 `auto-build` 端点未实现——层级图谱 (`/graph/hierarchy`) 只是运行时构建的只读视图，不持久化 `KnowledgeEntity`/`KnowledgeRelation` 记录。

**影响**：知识图谱无法跨会话累积、无法版本间对比演进、RAG 检索无法利用层级上下文。

### 1.2 前端：9 个设计组件缺失

设计文档 `batch-27-knowledge-sphere-design-spec.md` 定义了 14 个 UI 组件，但实际仅实现了核心页面（ReleaseBundles 列表/详情 + SphereTab 基础版）。**9 个组件完全缺失**，包括版本全景页、交互标注器、差异审核面板等关键交互。

**影响**：用户无法通过 UI 浏览版本演变全景、标注页面跳转关系、审核 AI 生成的模块差异、查看跨系统配置链路。

### 1.3 C-CONDITIONS：26 个孤儿条件游离追踪体系外

`C-CONDITIONS.md` 追踪 39 个条件，但历史批次中 **26 个条件从未迁移进追踪系统**。其中 **10 个仍需处理**（差异持久化、staging 演练、标注语料、灰度 SOP 等），**14 个已完成但无记录**，**2 个已过时**。

**影响**：Leader 条件追踪体系不可信——「已处理完」的条件和「仍需处理」的条件混在一起，Product 开工时无法准确评估债务。

## 2. 成功指标

| 指标 | 基线 | 目标 | 测量窗口 |
|------|------|------|---------|
| entity_type 覆盖率（设计 doc vs 代码） | 9/19 (47%) | 19/19 (100%) | PR 合入时 |
| relation_type 覆盖率（设计 doc vs 代码） | 9/18 (50%) | 18/18 (100%) | PR 合入时 |
| auto-build 端点可用 | 不存在 | 可接受 release_bundle_id，完整构建层级图谱并持久化 | PR 合入时 |
| 前端组件覆盖率（设计 spec vs 实现） | 3/14 (21%) | 14/14 (100%) | PR 合入时 |
| C-CONDITIONS 孤儿归位率 | 0/26 (0%) | 26/26 (100%) | PR 合入时 |
| 前端构建零错误 | 未知 | 0 TS 错误 + 0 ESLint 错误 | CI 通过 |

## 3. 非目标（本次不做）

- **C-CONDITIONS 中已有 Open 条件的实际修复**：只做孤儿归位（迁移进追踪器），不修复 C21/C22/C24 等现有 Open 条件
- **staging 环境验证**：C27-C1~C4 保持 Open，需 staging 环境就绪后单独 batch
- **新功能**：不扩展设计文档之外的新能力，仅补齐已设计但未实现的
- **vis-network 完整交互**：HierarchyGraph 升级到 vis-network 层级布局，但右键菜单、节点编辑等高级交互留到后续 batch
- **ModuleTimeline 的 module-level API**：如无现成端点，仅做 UI 组件 + mock 数据，后续 batch 补 API

## 4. 用户故事 + 验收标准

### 4.1 后端 auto-build

**US-1**: As a 测试工程师, I want 导入 release bundle 后一键构建知识图谱, so that 模块层级关系（版本→平台→模块→页面→用例）自动持久化为 KnowledgeEntity/KnowledgeRelation，支持跨会话查询和版本对比。

验收：
- Given 系统中存在一个已导入模块树的 ReleaseBundle / When 调用 `POST /api/v1/knowledge/graph/auto-build {release_bundle_id}` / Then 系统创建对应 entity_type=`release_bundle|platform|client_module|admin_module|page` 的 KnowledgeEntity 记录，并创建 relation_type=`belongs_to_version|has_platform|has_module|has_page|tested_by|navigates_to|configures|links_to_admin` 的 KnowledgeRelation 记录
- Given auto-build 已完成 / When 再次调用同 release_bundle_id / Then 系统返回 "already built" 且不重复创建

**US-2**: As a 测试工程师, I want auto-build 后在图谱中看到完整的层级关系, so that 可以直观理解模块组织结构和跨版本变化。

验收：
- Given auto-build 已完成 / When 调用 `GET /api/v1/knowledge/graph/hierarchy?release_bundle_id=X` / Then 返回包含所有层级节点的图谱数据，节点类型完整（release_bundle→platform→module→page）

### 4.2 前端版本全景页

**US-3**: As a 产品经理, I want 在版本全景页中以三列布局（APP/PC/WEB）浏览模块树, so that 可以对比三个平台的模块差异和页面跳转关系。

验收：
- Given 系统中有已导入模块树的 ReleaseBundle / When 访问 `/release-bundles/:id/panorama` / Then 左侧显示版本列表，右侧三列显示 APP/PC/WEB 平台的模块卡片
- Given 版本全景页已加载 / When 点击某个页面节点 / Then 右侧滑出 PageInteractionPanel，展示该页面的跳转关系（出向/入向/全局导航）

**US-4**: As a 测试工程师, I want 在截图上标注页面跳转热区, so that 可视化记录页面间的导航关系供测试用例生成使用。

验收：
- Given 某个模块有截图 URL / When 进入 InteractionAnnotator / Then 在截图上可拖拽画矩形框，完成后弹出目标页面选择器和交互类型选择器
- Given 标注完成 / When 保存 / Then 标注数据写入 `page_interactions` JSON 字段

### 4.3 差异审核面板

**US-5**: As a 测试工程师, I want 逐模块审核版本差异, so that 可以确认/修正/拒绝 AI 自动检测的模块变更。

验收：
- Given 版本 diff 已触发 / When 查看 DiffReviewPanel / Then 显示四个区域（新增/修改/删除/未变更），每个模块可展开查看页面级差异
- Given 审核完成 / When 点击 "确认全部" / Then 所有确认的差异通过 `POST /diff/confirm` 提交

### 4.4 知识图谱可视化

**US-6**: As a 测试工程师, I want 以层级力导向图浏览知识图谱, so that 直观理解项目知识球的整体结构和模块关联。

验收：
- Given 知识图谱中有数据 / When 访问知识中心 SphereTab / Then 显示 vis-network 层级布局图，节点按 entity_type 着色，边按 relation_type 着色
- Given 图谱已渲染 / When 切换边类型筛选 / Then 仅显示选中类型的边

### 4.5 C-CONDITIONS 孤儿归位

**US-7**: As a Team Leader, I want 所有历史 C 条件都在 C-CONDITIONS.md 中有记录, so that 条件追踪体系完整可信，Product 开工时不会遗漏历史债务。

验收：
- Given 26 个孤儿条件已识别 / When 迁移完成 / Then C-CONDITIONS.md 新增 26 条记录（14 Closed + 10 Open + 2 Closed/OBSOLETE），统计数字更新

## 5. 技术考量

### 依赖
- 后端 API 端点已全部存在，auto-build 是纯增量
- 前端所有所需 API 端点已存在，组件是纯 UI 层
- vis-network 已在 GraphTab 中集成，SphereTab 升级可复用

### 已知风险
- auto-build 在大量模块（200+）下的性能需关注，需分批 commit
- InteractionAnnotator 的画框交互涉及原始 DOM 事件处理，需仔细处理坐标转换
- 层级图谱在 200 节点下的渲染性能需验证（C27-C2）

### 待解决问题
- auto-build 幂等性：如何判断 "already built"？按 release_bundle_id 查已有 entity，或加 `built_at` 时间戳
- page 实体的 entity_key 格式：设计文档未明确定义，需确定（建议 `page:{module_key}:{page_name}`）

## 6. 上线计划

| 阶段 | 受众 | 成功门槛 |
|------|------|---------|
| PR 合入 | 开发团队 | 代码 review 通过 + CI 绿 |
| 本地验证 | QA | 手动验证全景页 + auto-build + 图谱渲染 |
| staging | 内部用户 | C27-C1~C4 staging 验证（后续 batch） |
