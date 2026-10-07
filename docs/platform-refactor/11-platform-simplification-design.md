---
title: "平台全面简化设计：删除清单与实施（用户 2026-10-07 定稿方向）"
owner: "qa-team"
created: "2026-10-07"
last_reviewed: "2026-10-07"
status: "active"
tags: ["platform-refactor", "simplification", "delete-list", "ai-cutdown"]
related:
  - "docs/platform-refactor/01-platform-positioning-and-mainline.md"
  - "docs/platform-refactor/02-function-abc-whitelist.md"
  - "work-logs/platform-simplification-production-eval-20261007.md"
---

# 平台全面简化设计：删除清单与实施

> 本文是本次「全面简化」的**执行事实源**，取代 02 白名单中与本轮用户决策冲突的部分（AITDE 由 A 级改为删除）。
> 用户 7 项已确认决策：① 以生产证据评估为准；② AI 只保留「需求→AI 生成用例」，AITDE/DSH 全删；
> ③ 报告中心/测试数据集/通知配置/集成配置/组织管理/主题实验室删除；④ 知识中心只留项目知识库；
> ⑤ 定时任务 + API Token 保留，open_knowledge/knowledge-mcp 删除；⑥ 代码 + 数据库表全部删除；
> ⑦ 一次性大 PR（方案 A）。
> 配套评估结论见 `work-logs/platform-simplification-production-eval-20261007.md`。

## 1. 简化后最终形态

**一级入口（≤4）**：① 我的待办（工作台）② 版本验收（版本任务/版本发布包/需求文档）③ 缺陷
（结果与缺陷组中报告中心删除后仅剩缺陷，组可拆平为单入口）④ 知识库（项目知识 3 Tab）。

**专家区**：资产（用例服务/接口测试/UI 自动化/目标环境）、引擎与配置（AI 配置/蓝湖证据包）、
个人（定时任务/我的项目）、系统（系统管理）。

**AI 能力**：仅「需求文档 → AI 生成用例」+ AI 配置中心（提供方池）+ 蓝湖证据采集。
安全守卫保留：url_guard / spec_guard / token 白名单 / 执行沙箱 / ai_guard（额度闸门）/ 出网白名单。

**执行能力**：ExecutionJob 协议 + `cameltv-node` 本地节点（scripts/node/）保留；
老队列冻结面（ui_test_service 内置浏览器路径 C263-1）随本次一并收口评估。

## 2. 删除清单（代码 + 库表，含规模）

### 2.1 AITDE 全家

| 位置 | 规模 | 处置 |
|------|------|------|
| `backend/app/modules/aitde/` | 180 文件 / 22,896 行 | 删除 |
| `backend/app/modules/campaign_execution/` | 5 文件 / 488 行 | 删除 |
| `backend/app/api/v2/` | 27 文件 / 2,923 行 | 删除（`main.py` L13/L217 摘除） |
| `backend/app/temporal/` | 3 文件 / 240 行 | 删除 |
| `backend/app/models/production_evidence.py` 及引用 | — | 删除 |
| 前端 pages：missions(37)/executions(7)/campaigns/healing/flaky/fixtures/data-sources/production(16)/ai-suggestions/regression-selections/admin(GovernancePage+ai-evaluations) | 16 目录约 13,100 行 | 删除 |
| 前端 api/：actionPlans/aiClosedLoop/aiOperations/ambiguities/apiContract/browserInteractions/continuous/contract/dataPlans/dataRequirements/dataSources/executions/fixtures/governance/healingProposals/…（aitde 域） | — | 删除 |
| `components/AitdeGate.tsx` + `config/aitde.ts`（运行时读 `/api/v2/health` 的开关体系） | — | 删除（router 23 处 AitdeGate 门控路由随之删除） |
| `deploy/aitde-runtime/`、docker-compose 中 temporal/worker 服务 | — | 删除 |
| `tests/` 中 aitde/v2/temporal 测试 | — | 删除 |

### 2.2 DSH / Agent / AI 本地管线

| 位置 | 处置 |
|------|------|
| `backend/app/api/v1/dsh_tasks.py`、`agent.py`、`open_knowledge.py` | 删除（router.py 摘除） |
| `backend/app/services/dsh/`（12 文件） | 删除 |
| `backend/app/models/dsh_task.py`、`ai_job.py`（AiJob/AiResult）、`ai_task.py`(核实)、`ai_shadow_run.py`、`ai_response_cache` | 删除 |
| `backend/app/ai_gateway_app.py`（本地推理网关进程） | 删除或收敛（见 D9） |
| `services/ai_gateway/`、`ai_job_dispatch.py`、`ai_agent.py` 的 /jobs 端点 | 按 D9 决策 |
| 前端 pages：dsh-tasks(8)/ai-jobs | 删除 |
| `knowledge-mcp/`（仓库根目录，Batch 202） | 目录删除 |

⚠ **关键事实（子代理盘点）**：`ai_platform_inference=False` 是默认值 → 需求→AI 生成用例的生产默认
路径走 `ai_job_dispatch` → `AiJob` 本地 Agent 派发。删除 AI 本地管线前必须先把需求 AI 生成切回
**平台直连 LLM**（`requirement_ai_generate.py:149-153` 改调 `ai_service` 直连），否则保留的 AI 能力会断。
另：`AiAgentToken` 模型 + `POST /ai/agents/register`（令牌签发）+ `verify_agent_token` 是
`execution_jobs`/`cameltv-node` 的节点鉴权（drill_b1_e2e.py L264/453、cli.py L289-292）→ **保留**
（可改名 node_token，不删）。`AiAgent` 模型同留（节点注册表）。

### 2.3 六个非 AI 模块

| 模块 | 后端 | 前端 | 模型 |
|------|------|------|------|
| 报告中心(+质量追溯 Tab) | `api/v1/report.py`、`trace.py`、`report_service.py`、`report_aggregator.py`、`coverage_report.py`、`statistics_service.py`(核实)、`template.py` | pages/report(6) | `test_report.py`、`report_template.py` |
| 测试数据集 | `api/v1/dataset.py`、`dataset_service.py`、`pilot_dataset_service.py`(核实) | pages/dataset | `dataset.py` |
| 通知配置 | `api/v1/notify.py`、`notify_service.py` | pages/notify(3) | `notification.py` |
| 集成配置 | `api/v1/integration.py`、`integration_service.py`、`elk_service.py`、`services/sync/`(核实) | pages/integration(3) | `integration.py`、`sync_log.py` |
| 组织管理 | `api/v1/organization.py`、`organization_service.py` | （入口已收敛进我的项目） | `organization.py` |
| 主题实验室 | — | pages 目录 + theme-lab/ + ui-concepts/ | — |

### 2.4 知识中心收敛

- 删除 Tab：知识图谱（`knowledge_graph.py`、`entity_service.py`、`graph_builder.py`、`vector_store.py`、
  `embedding_service.py`、`vectorize.py`）、AI 审核台（`knowledge_artifacts.py`、`artifact_service.py`、
  `snapshot_service.py`、`skill_service.py`、`agent_orchestrator.py`、`agent_queue.py`、`agent_prompts.py`、
  `agent_run_service.py`、`change_detector.py`、`regression_predictor.py`、`llm_json_client.py`(核实)）、
  平台研发；模型 KnowledgeEntity/KnowledgeRelation/AiArtifact/AgentRun/AgentQueueItem/KnowledgeIteration/Snapshot。
- 保留：知识源 CRUD/检索（`knowledge_core.py` + source/chunk/vector 最小集，**保留向量检索**
  （`search_service`/`vector_store`/`embedding_service` 属项目知识检索链路，与图谱共用件按调用核实拆分））、
  wiki 页面核心（`wiki_core.py` + 核心 service；LLM 差异对比 `external_llm_wiki.py`/`contract_extractor.py`
  等 AI 部分删除）、`ImpactTab`（知识中心影响面查询，`/api/v1/impact` 保留）。
- ⚠ 保留模块对 knowledge 服务的引用需逐一核实：`requirement_modules_*`（模块树/交互标注 LLM 提取器——
  属需求模块功能，保留）、`release_bundles_diff.py`（version_differ，LLM 差异对比——核实是否属发布包核心）、
  `apitest_*/defect/test_case_crud`（ingest_service 落知识源——保留）、`lanhu_evidence`（chunk/source/ingest——保留）。

### 2.5 旧体系与死代码

| 项 | 依据 | 处置 |
|----|------|------|
| 旧版本任务体系 `version_mission.py` + `case_generation_service.py` + AgentWorkLog/GeneratedArtifact/VersionMission 模型 | V1_DEPRECATIONS 已标 2027-01-01 sunset；前端 /version-mission 重定向 /release-bundles | 删除 |
| `pilot_dataset_service.py`/`pilot_slo_service.py` | app 零调用者（仅单测引用） | 删除 |
| `openvpn_service.py`/`ffmpeg_service.py`/`tencent_executor.py` | app 零调用者；配置默认关 | 删除（先复核 deploy 脚本无外部调用） |
| `convergence.py` + `convergence_service.py` | 无前端页面、无菜单种子（B14 一次性收敛工具面） | 删除 |
| `report_aggregator.py` | dashboard.py L95 引用其汇总 → 先抽离到 statistics/dashboard_service | 删除 |
| `quality追溯 trace.py` | 前端 Tab 已并入报告中心，报告中心删除 | 删除（工作台统计改走 statistics_service） |

## 3. 必须的改造点（删除引发的隐藏依赖）

| # | 位置 | 改造 |
|---|------|------|
| R1 | `deps.py`(5)/`auth_service.py`(4)/`project_service.py`(3)/`rbac_service.py`(1) | 组织概念删除：权限数据范围改「项目成员」直管；去掉 personal 组织创建与成员校验；`Project.organization_id` 列 DROP |
| R2 | `project.py:192/219`、`open_api.py:305` | 质量门禁配置从 `report_service` 抽到独立 `quality_gate_service`（模型 `quality_gate.py` 保留）；`get_report_gate` 语义随报告删除收敛 |
| R3 | `auth.py:257`（密码重置邮件） | ⚠ 决策点：见 §6-D3。若保留密码重置，则保留 env 级 SMTP 发送最小函数；若删除则连带删除 forgot/reset-password 页面 |
| R4 | `defect.py:44`、`test_case_crud.py:306`、`test_plan_execution.py:43`、`playwright_executor.py:248`、`open_api.py:95/191`、`test_plan_service.py:1118` | 摘除 notify_sync/queue_notification 调用（事件订阅体系删除）；失败自动链路只留「转缺陷」 |
| R5 | `api_execution_service.py:1469` | 摘除数据集参数注入分支（`dataset_id`/`${变量}` 功能随数据集删除） |
| R6 | `test_plan_service.py:25` | 摘除 ELK kibana 链接/trace_id（随集成删除） |
| R7 | `services/ai_service.py` L1247-1294 | 摘除 DSH harness 模式与降级路径，只留直连 |
| R7b | `requirement_ai_generate.py` L149-153 | 需求 AI 生成切回平台直连（去 `ai_job_dispatch` 依赖，见 D9） |
| R7c | `version_task_exec_service.py` L177 | 把依赖的 `aitde.evidence.snapshot_sanitizer` 抽为独立 util（版本任务保留） |
| R7d | `test_plan_crud.py` L17、`test_case_service.py` L258 | 摘除/抽离 `aitde.legacy_cutover.CompatibilityPolicy` 依赖 |
| R7e | `modules/campaign_execution/service.py` L11-17 | **计划/接口执行运行时保留**：将其依赖的最小执行模型（ExecutionRun/EnvironmentSnapshot/ScenarioAdapter 等）从 aitde 抽离为独立模块（如 `app/modules/execution_runtime` 或并入 app/models），campaign_execution 改依赖新模块 |
| R7f | `v1_deprecation.py` | replacement_v2 注册表清空（/api/v2 删除后） |
| R7g | `evidence_bundle_service` | 复用 aitde.assertion.completeness 口径 → 抽为本地常量/util |
| R8 | `main.py` L13/L217 | 摘除 v2 router；核实 agent 队列启动与 temporal 生命周期 |
| R9 | `models/__init__.py` | 摘除被删模型导入 |
| R10 | `seed.py` | 菜单种子删除（missions/runtime/dsh_tasks/report/dataset/integration/notify 等）+ 权限点删除 |
| R11 | 前端 `router/index.tsx` | 删除 AITDE 门控路由（23 处 AitdeGate）与删除页路由；`/trace`、`/playground`、`/agent-workbench` 等重定向源同步删除；登录默认落地确认回 `/workbench` |
| R12 | `nav-config.ts` | MAIN_ROW_DEFS ②版本验收去 `menu:missions`、③结果与缺陷去 `menu:report`（组剩 defect 可拆平）；EXPERT_BUCKET_DEFS 资产桶去 dataset、引擎与配置桶去 dsh_tasks/runtime/integration/notify；EXPERT_KEEP_CODES 同步去 dataset；`PRIMARY_ENTRY_LIMIT=4` 断言随新蓝图更新 |
| R13 | `menu_service.py` | HIDDEN_MENU_CODES/DISABLED_MENUS 中本次硬删的 code 直接移除（不再需要软下线占位）；AITDE 按 flag 隐藏逻辑删除 |

## 4. 数据库迁移

- Alembic 迁移（带「表存在检查」守卫，对齐 b191 幂等惯例）：DROP 表——
  aitde 全族（mission/scenario/contract/scope/source/run/workflow/healing/flaky/fixture/data_source/campaign/
  ai_eval/…按 models 清单）、dsh_task、ai_job/ai_task/ai_result/ai_shadow_run/ai_response_cache、
  test_report/report_template、dataset、notification_*、integration_config/sync_log、
  organization/organization_member、production_evidence、knowledge graph/artifact 相关表。
- 列级：`projects.organization_id` DROP。
- 生产执行前必须备份（batch-262 恢复演练链路已验证：pg_dump 67M → pg_restore → 抽查 → 20s）。

## 5. 配置与部署清理

- `config.py`：删 `aitde_v3_enabled`/`version_mission_write_stage`/`dataset_write_stage` 等 AITDE 开关、
  DSH_* 全家、temporal_*、对象存储 aitde 相关；保留执行沙箱/出网白名单/ai_guard 相关。
- `.env.example`、`deploy/docker-compose*.yml`、frontend Dockerfile ARG（AITDE 构建开关）同步清理。
- `requirements.txt`：删 temporalio（+ DSH/本地 AI 专属依赖，按子代理结论）。
- 前端 `config/aitde.ts` 删除；`package.json` 清 AITDE 专属依赖。

## 6. 决策点（2026-10-07 用户已全部确认 ✅）

- **D1 ✅ 保留**：版本验收任务 + ExecutionJob/cameltv-node + 影响图（知识中心 ImpactTab）+ campaign_execution
  （抽离最小执行模型为独立模块，计划/接口执行不回归）。
- **D2 ✅ 切回平台直连**：需求 AI 生成改走 ai_client + ai_config_service + ai_guard 直连；
  删除 ai_job_dispatch/AiJob/AiResult/ai_agent jobs/ai_gateway 影子缓存/ai-jobs 页；
  保留 AiAgentToken/AiAgent（cameltv-node 节点鉴权）。
- **D3 ✅ 保留最小邮件**：env 级 SMTP 发送最小函数（`send_password_reset_email` 迁移到独立 mail util，
  无配置页）；忘记/重置密码页保留；通知渠道/订阅体系删除。
- **D4 ✅ 删除**：metrics/onboarding/pilot_dataset_service/pilot_slo_service/openvpn_service/ffmpeg_service/
  tencent_executor/convergence/report_aggregator（dashboard 汇总抽离到 statistics/dashboard_service）。
- **D5 ✅ 保留**：接口用例 AI 生成/泛化（api_case_generation_service/api_generalization_service）。
- **D6 ✅ 保留只读**：test_plan 只读 API + 历史表保留（137,642 行执行历史是统计底座）；删除写入口面。
- **D7 ✅ 删除**：旧版本任务体系 version_mission + case_generation_service + 相关模型。
- **D8 ✅ 删除**：死代码（见 §2.5）。
- **D9 ✅ 验收时处理**：生产重录有效 DeepSeek Key（batch-273 取证 4 Key 全 401）。

## 7. 回归与验收（PR 内完成）

1. 后端：`ruff check app/ --select F821`、受影响模块 pytest、`tests/test_route_inventory.py`（路径集基线同步）、
   `tests/test_route_layer_orm_ban.py`、alembic 单头校验 + 迁移幂等守卫。
2. 前端：`npm run typecheck && npm run build`、vitest（删除对应测试文件）、导航断言
   （PRIMARY_ENTRY_LIMIT=4 模型测试同步）。
3. 浏览器冒烟（frontend-verify）：登录 → 导航只剩保留清单 → 核心页（版本任务/用例/接口/UI/需求 AI 生成）
   可操作、无 404、console 无报错。
4. 生产部署后验收：菜单种子对账（batch-271 方法复用）、登录落地、`/api/v2` 404、删除表不残留。

## 8. 实施方式

- 独立 worktree `F:\CamelTv-worktrees\DeepSeek_Harness-platform-simplification`（已建，分支
  `feature/platform-simplification`，base=origin/main@5a36dbf96，元数据校验通过）。
- 一次性大 PR 指向 main；push 前展示变更范围并逐次确认（AGENTS.md §2.4 直接任务门禁）。
