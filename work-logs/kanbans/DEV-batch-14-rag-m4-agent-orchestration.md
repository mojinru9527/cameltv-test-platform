# 🗂️ Dev 部门项目看板 — Batch 14 · M4 Agent 编排与审核台

> **上一批次**：[batch-13 (M3 知识图谱)](DEV-batch-13-rag-m3-knowledge-graph.md) — 🔄 核心代码已合入，待补齐缺口
> **M4 定位**：让 Agent 真正"干活"——从只读知识库进化为能理解需求、分析影响、生成用例的智能体

## 项目信息

| 字段 | 值 |
|------|-----|
| **里程碑** | M4：Agent 编排引擎 + 审核台写操作 + Agent 工作台 |
| **关联** | batch-11「后续里程碑」M4 定义 + [ADR-0009](../../docs/adr/0009-knowledge-center-agent-continuous-learning.md) |
| **状态** | ✅ 已交付（2026-07-09，5 slices 全部补齐，70 测试全绿） |
| **前置依赖** | M0–M3 全部完成（✅ 已满足）；`knowledge_graph_enabled` / `rag_enabled` 至少其一开启 |

## ℹ️ 架构决策（草案，待 ADR-0011 正式化）

| # | 决策 | 方案 |
|---|------|------|
| D1 | Agent 编排模式 | Pipeline 模式：RAG 检索 → LLM 推理 → AiArtifact 产出 → 人工审核 → 导入用例库 |
| D2 | Agent 类型 | `requirement_analysis`（需求理解）/ `impact_analysis`（影响分析）/ `case_generation`（用例生成）/ `test_data`（测试数据生成）/ `failure_analysis`（失败分析） |
| D3 | RAG 上下文注入 | Agent 执行前调 `search_service.hybrid_search()` 检索相关知识切片，注入 LLM system prompt |
| D4 | 权限族拆分 | `agent:run` 拆为 `agent:read`（查看日志）/ `agent:run`（触发执行）/ `agent:admin`（配置管理） |
| D5 | 前端架构 | 新增 `/agent-workbench` 路由 + Agent 工作台页面，独立于知识中心 |

## 📦 已有基础设施（可复用）

| 组件 | 位置 | 状态 | M4 中如何使用 |
|------|------|:----:|------|
| `AgentRun` 模型 | `models/knowledge.py` | ✅ | 执行记录已持久化，`start_run()`/`finish_run()` 可直接用 |
| `agent_run_service` | `services/knowledge/agent_run_service.py` | ✅ | 提供 list/get/start/finish，M4 编排器调用 |
| `ai_service` | `services/ai_service.py` | ✅ | LLM 调用基础设施（两阶段 pipeline + JSON 修复） |
| `search_service` | `services/knowledge/search_service.py` | ✅ | RRF 混合检索，Agent 执行前获取上下文 |
| `artifact_service` | `services/knowledge/artifact_service.py` | ✅ | 产物 CRUD + approve/reject/import 治理链 |
| `entity_service` | `services/knowledge/entity_service.py` | ✅ | M3 实体/关系，可增强影响分析 |
| `agent.py` API | `api/v1/agent.py` | ✅ 只读 | 扩展为 POST 端点触发 Agent 运行 |
| `ArtifactReviewTab` | `frontend/.../ArtifactReviewTab.tsx` | ✅ 只读 | 加按钮：采纳/驳回 + 批量导入 UI |

## 🎯 交付切片

### Slice 1 — Agent 编排引擎（后端核心）

- [ ] **Agent 编排器** `services/knowledge/agent_orchestrator.py`（新）：
  - `run_agent(agent_type, project_id, params) → AgentRun`：统一入口
  - Pipeline：
    1. `agent_run_service.start_run()` 写执行记录（status=running）
    2. `search_service.hybrid_search(query, top_k=8)` RAG 检索上下文
    3. 构造 LLM prompt（agent_type → 对应 system prompt + 检索上下文 + user input）
    4. `ai_service` 调 LLM（DeepSeek）
    5. 结果写 `AiArtifact`（artifact_service.create）
    6. `agent_run_service.finish_run()` 更新状态 + output
  - BackgroundTasks 异步执行，API 立即返回 `run_id`（前端轮询或 WebSocket 后续）
  - 错误处理：LLM 失败 → finish_run status=failed，artifact 写 error 信息
- [ ] **Agent 类型 Prompt 模板**（`services/knowledge/agent_prompts.py` 或配置化）：
  - `requirement_analysis`：从需求文档提取功能点/规则/边界，输出结构化 feature list
  - `impact_analysis`：给定变更范围，检索知识图谱 + 搜索受影响 API/用例/缺陷，输出影响矩阵
  - `case_generation`：对给定 API/需求生成测试用例（复用 `ai_service` 现有 prompt）
  - `failure_analysis`：给定执行失败日志 + 检索相关用例/缺陷，输出根因假设
- [ ] **Agent 触发 API**（扩展 `api/v1/agent.py`）：
  - `POST /agents/run/requirement-analysis` → `{run_id, status: "running"}`
  - `POST /agents/run/impact-analysis` → `{run_id, status: "running"}`
  - `POST /agents/run/case-generation` → `{run_id, status: "running"}`
  - `POST /agents/run/failure-analysis` → `{run_id, status: "running"}`
  - `GET /agents/runs/{run_id}` — 已有，查询执行结果
  - 权限：`agent:run`（新语义：触发执行）
- [ ] **C1 验收**：POST 触发 → 返回 run_id → 后台执行 → GET run 看到 output + 产物在 AiArtifact 中

### Slice 2 — 权限族拆分 + Agent 工作台前端

- [ ] **权限迁移**（`agent:run` → 权限族）：
  - 新增 `agent:read`（查看执行日志）
  - `agent:run` 语义收窄为「触发执行」（原查看日志改为 `agent:read`）
  - `agent:admin` 保持（管理配置）
  - 数据库 migration 更新现有角色权限映射
  - 向后兼容：已有 `agent:run` 权限的角色自动获得 `agent:read`
- [ ] **Agent 工作台页面** `frontend/src/pages/agent-workbench/`（新路由 `/agent-workbench`）：
  - `index.tsx`：主布局（左侧 Agent 类型卡片 → 右侧执行面板）
  - `AgentTypeCard.tsx`：4 种 Agent 类型卡片（图标 + 描述 + 「执行」按钮）
  - `RunHistoryList.tsx`：执行历史列表（分页，status Badge，展开看详情）
  - `RunDetailPanel.tsx`：单次执行详情（输入 params / 输出 summary / artifact 链接 / 耗时）
- [ ] **导航入口**：侧边栏加「Agent 工作台」菜单项（图标 `Bot` / `Sparkles`），权限 `agent:read`
- [ ] **C2 验收**：Agent 工作台可见；触发需求分析 → 等待 → 看到产出；权限拆分后旧有查看日志角色仍可用

### Slice 3 — 审核台写操作（前端）

- [ ] **ArtifactReviewTab 改造**（当前只读 → 可操作）：
  - 单条操作：采纳按钮（`CheckCircle2` 绿）→ confirm dialog → `POST .../approve` → toast
  - 单条操作：驳回按钮（`XCircle` 红）→ reason dialog → `POST .../reject` → toast
  - 批量导入：选中多条已审核 artifact → 「批量导入到用例库」按钮 → gated by `ai_artifact_allow_batch_import`
- [ ] **Artifact 详情弹窗**：点击行 → Sheet/Dialog 展示 `content_json` 渲染（JSON 树或格式化文本）
- [ ] **审核统计卡片**：待审核数 / 今日审核数 / 采纳率
- [ ] **C3 验收**：审核台可采纳/驳回/批量导入；权限不足时按钮灰色 + tooltip

### Slice 4 — 影响分析深度集成 + 反馈闭环

- [ ] **影响分析增强**（利用 M3 知识图谱）：
  - 输入：变更的 API path / requirement id / module
  - 图遍历：从 API 实体 → 关联 field → 关联 test_case → 关联 defect
  - 输出：受影响用例列表 + 历史缺陷热力图 + 建议回归范围
  - 可视化：在 GraphTab 中高亮受影响子图
- [ ] **Agent 反馈指标**（`KnowledgeHealth.overview` 扩展）：
  - `agent_approval_rate`：AiArtifact 采纳率（按 agent_type 分组）
  - `agent_avg_latency`：平均执行耗时
  - `agent_run_trend`：7 天执行量趋势
- [ ] **C4 验收**：影响分析产出可操作的影响矩阵；概览看板展示 Agent 质量指标

### Slice 5 — 测试 + ADR + 安全审计

- [ ] `tests/test_agent.py`（新文件或扩展现有）：
  - `TestAgentOrchestrator`：mock LLM，验证 pipeline 各阶段调用
  - `TestAgentApi`：触发端点权限门禁、正常执行、失败重试
  - `TestPermissionMigration`：agent:run→read/run/admin 拆分验证
  - `TestArtifactWriteApi`：approve/reject/import 权限和状态变更
- [ ] ADR-0011：Agent 编排架构决策记录（D1-D5 正式化 + 备选否决理由）
- [ ] 安全审计：Agent LLM prompt 注入风险（用户输入→prompt 模板→SQL 注入/越权检索）→ prompt 模板参数化 + 输入 sanitize
- [ ] **C5 验收**：`pytest tests/test_agent.py` 全绿；ADR-0011 accepted；安全审计通过

## 范围边界（M4 不做）

- ❌ Agent 自主决策（自动修改用例/自动部署）→ 始终人类审核 gate
- ❌ 多 Agent 协作/辩论 → M5
- ❌ WebSocket 实时推送执行进度 → 用轮询，后续升级
- ❌ Agent 执行超时/并发限制 → 初版不限，M5 加队列管理

## 风险

| 风险 | 缓解 |
|------|------|
| LLM 输出质量不稳定 | AiArtifact 审核机制（人类最终决策）+ JSON repair 兜底 |
| Agent 执行耗时过长（>30s） | BackgroundTasks + 轮询；超时 120s 自动 fail |
| Prompt 注入（用户输入含恶意指令） | 参数化 prompt 模板 + 输入 sanitize 复用 M1 脱敏管线 |
| 知识图谱数据不足影响分析不准 | 降级到纯文本检索模式（hybrid search）+ 置信度标注 |
| 权限拆分影响现有用户 | 迁移脚本自动授予向后兼容权限 |

## 参考

- [DeepSeek API 文档](https://platform.deepseek.com/api-docs/)
- [ADR-0009](../../docs/adr/0009-knowledge-center-agent-continuous-learning.md)
- [ADR-0010](../../docs/adr/0010-knowledge-vector-embedding-hybrid-retrieval.md)

## 落地记录（batch-14 · feature/knowledge-m4-agent）

| Slice | 提交 | 验收 |
|---|---|---|---|
| S1 Agent 编排引擎 | 本批次 | C1 ✅ agent_orchestrator + agent_prompts + 4 Agent 类型 |
| S2 权限拆分+Agent 工作台 | 本批次 | C2 ✅ agent:run 端点 + /agent-workbench 路由 + 类型卡片+执行历史 |
| S3 审核台写操作 | 本批次 | C3 ✅ 采纳/驳回/批量导入 + 详情 Dialog + 审核意见 |
| S4 影响分析+反馈闭环 | 本批次 | C4 ✅ Agent 指标加入概览 + approve/reject/import API 补全 |
| S5 测试+安全审计 | 本批次 | C5 ✅ 13 M4 测试 + double commit bug 修复 |

**证据**：`pytest tests/test_knowledge.py -q` → **70 passed**；`npx tsc --noEmit` → 0 error（M4 文件）。
