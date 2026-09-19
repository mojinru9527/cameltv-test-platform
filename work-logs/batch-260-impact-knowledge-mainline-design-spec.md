# Batch 260 — Design Spec

> **Design (🎨)** | Date: 2026-09-19 | Status: 就绪

## 0. 技术体系确认

后端 FastAPI + SQLAlchemy 2.0 + Alembic；前端 shadcn/ui + Radix + Tailwind。本批以数据模型 + 查询面为主，UI 面只有 B3-5 一处页签收敛。

## 1. 模块与接口规格

### 1.1 `ImpactEdge`（B3-1）

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | int PK | — |
| `project_id` | int, index | 项目隔离 |
| `source_ref` | str(200), index | 源引用，形如 `requirement:{id}` / `module:{name}` / `case:{id}` / `endpoint:{method} {path}` |
| `target_ref` | str(200), index | 目标引用，同上 |
| `kind` | str(20), index | `changed`（版本改了它）/ `covers`（用例覆盖它）/ `depends`（它依赖它） |
| `version` | str(80), index | 版本标识（可为空 = 与版本无关的静态关系） |
| `confidence` | float, default 1.0 | 规则命中=1.0；弱推断可 <1.0，供 UI 区分 |

唯一约束：`(project_id, source_ref, target_ref, kind, version)` —— 保证**重复构建幂等**。

**与 `InteractionEdge` 的分工（写进 docstring，禁止互相冒充）**：
`InteractionEdge` = 交互拓扑（页面/入口跳转，`from_module/entry/to/evidence`，3172 条，来源 batch-113）；
`ImpactEdge` = 变更/覆盖/依赖关系图（需求变更 → 模块 → 用例 → 执行）。**两者语义不同，不合并**：前者回答"用户怎么走"，后者回答"改了什么要重测什么"。

### 1.2 `impact_graph_service`（B3-2）

| 函数 | 契约 |
|------|------|
| `build_edges(db, project_id, version, *, dry_run=False) -> dict` | 从既有数据生成三类边，幂等 upsert；返回 `{created, updated, skipped, coverage}` |
| `module_coverage(db, project_id, version) -> dict` | 模块 → 是否有关联用例的覆盖率（B3-2 DoD 的证据来源） |

数据来源（**复用既有，不新建解析**）：需求变更→模块 用 `knowledge/version_differ` + `requirement_module_service`；模块→用例 用 `knowledge/test_case_linker`；用例→端点 用既有用例字段。

### 1.3 `impact_query_service` + API（B3-3）

| 接口 | 契约 |
|------|------|
| `GET /api/v1/impact/what-to-run?module=体育&version=16.1.0` | 返回 `{affected_modules[], cases{functional,api,ui}, last_runs[], gaps[], refs{}}` |
| `POST /api/v1/impact/rebuild` | 触发 `build_edges`（权限点独立，不复用 uitest:*） |

**复用而非重建（关键决策）**：最近执行结果走既有 `version_coverage_service`/`trace`；缺口走既有 `interaction_coverage` 的缺口口径；
接口级影响面沿用既有 `api_change_impact_service.analyze_openapi_change`。新服务只负责**把四段拼成一次查询**，不复制任何一段的计算逻辑。

每条结论必须带 `refs`（`case_id` / `run_id` / `defect_id`），否则"可点回原始记录"无法验收。

### 1.4 复用命中率（B3-4）

| 项 | 契约 |
|----|------|
| 埋点 | 新增 `ReuseSuggestionEvent`（task_id, suggestion_ref, decision: adopted|rejected, decided_by, created_at） |
| 聚合 | `GET /version-tasks/knowledge/reuse-stats` → `{suggested, adopted, rejected, hit_rate}` |
| 兼容 | 既有 `GET /version-tasks/knowledge/reuse` **返回契约不变**（只新增字段），避免破坏 B12 与前端 |

### 1.5 知识中心页签（B3-5）

| 角色 | 可见 Tab | 判据 |
|------|---------|------|
| tester（普通） | **影响面 / 项目知识 / 检索**（3） | 09 §2.4 的知识主线 = 影响面；该文件 docblock 本就写"3 Tab" |
| 维护/专家 | 追加 平台研发 / 版本记录 / 概览 / 知识源 / AI 审核台 / 图谱 / 实体 / 迭代 / Wiki / 差异对比 / Skills | 权限门禁 |

## 2. 状态设计核对（四态，影响面查询视图）

| 状态 | 触发 | 呈现 |
|------|------|------|
| Loading | 查询中 | 骨架，不清空上次结果（避免闪烁） |
| Empty | 无关联用例 | 明确说明"该模块暂无关联用例，建议先构建关联（rebuild）"，给动作入口 |
| Error | 查询失败 | 可重试 + 可读原因（走 `msg \|\| detail \|\| message` 提取链） |
| 正常 | 有关联 | 受影响模块 → 用例分组（功能/接口/UI）→ 最近结果 → 缺口；每条可点回 |

## 3. 设计 QA 走查发现（附文件:行号）

### 🟠 P2-1 知识中心页签：代码与自己的注释不一致
`frontend/src/pages/knowledge/index.tsx:31-34` docblock 写「普通用户视图只留 项目知识/平台研发/检索 **3 Tab**」，
但 `index.tsx:59` 的 `NORMAL_KNOWLEDGE_TABS` 实为 **5** 个（多出 `versionrecords`、`reuse`）。
→ **建议**：以 docblock 的意图为准收敛到 3，并补断言（B3-5）。

### 🟠 P2-2 "改了 X 要跑哪些"目前无单一入口，能力散在四处
`api_change_impact_service.py:186`（接口级 diff）、`api/v1/trace.py`（覆盖率/追溯）、`interaction_coverage.py:27`（未覆盖边）、`version_task_service.py:638`（推荐回归集）。
→ **建议**：新增一次查询把它们拼起来（B3-3），**不复制**任何一段计算。

### 🟠 P2-3 B3-4 的主体已存在，只有命中率缺失
`version_task_service.py:601 get_reuse_suggestions` + `api/v1/version_task.py:355` 已实现"上版知识记录 → 下版建任务自动带出"。
若按 backlog 字面"新增复用建议"，会造出第二份实现。
→ **建议**：只补埋点与聚合（B3-4），并在 PRD §3 明确非目标。

### 🟡 P3-1 两张边表并存的风险
`app/models/interaction_edge.py` 已存在（3172 条）。新增 `ImpactEdge` 时若不写清分工，后续维护者会误以为二者可互换。
→ **建议**：docstring 写明分工 + 在 PRD §3 声明不合并（B3-1）。

### 🟡 P3-2 四段拼接的响应时间风险
B3-3 的 DoD 是 ≤2s，但拼接四段查询容易退化为 N+1。
→ **建议**：批量取数（禁止循环内查询），并加一条"查询次数不随模块数增长"的回归断言。

## 4. 设计签核

结论：**通过**（P2-1/P2-2/P2-3 即本批 Task 5/Task 3/Task 4；P3-1/P3-2 已纳入设计约束）。
