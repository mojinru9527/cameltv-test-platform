---
title: "CamelTv AI Quality Engineering Platform — 工程规格书（合并版 v1）"
owner: "qa-team"
created: "2026-11-09"
last_reviewed: "2026-11-09"
status: "active"
version: "v1.3-baseline-aligned"
tags: ["platform-refactor", "ai-agent", "engineering-spec", "developer-ready"]
related:
  - "docs/platform-refactor/09-platform-landing-plan.md"
  - "docs/platform-refactor/11-platform-simplification-design.md"
  - "docs/platform-refactor/12-ai-quality-agent-landing-plan.md"
  - "work-logs/platform-simplification-production-eval-20261007.md"
  - "docs/standards/test-asset-map-standard.md"
  - "tests/test-case-standards/interaction-testing/interaction-methodology.md"
  - "docs/aiqe/baseline.md"
---

# CamelTv AI Quality Engineering Platform — 工程规格书（合并版 v1）

> 面向：平台开发团队（直接按此写代码）。
> 口径：本文是**开发级目标模型 + 字段/API 契约 + 状态机 + Driver 协议 + Agent Contract + 代码骨架 + 任务拆分 + 验收场景**。
> 立场：**复用现有平台 + 复用成熟开源 + 平台自研编排/证据/质量治理，不重造浏览器和测试框架**。
> 本文合并了 [12 号落地方案（本仓）](12-ai-quality-agent-landing-plan.md) 与"另一 Agent 的 v2.0 Spec"两份输入的强项：
> - **数据模型 / 状态机 / Workflow DAG / Event 协议 / 噪音治理 / E2E 验收 / OSS 准入 / 安全治理** 来自 v2.0；
> - **P0 先修 / 不做清单（AITDE 教训） / 现有代码接缝 / 24 准则+asset-map 复用 / Agent Skills 开放标准** 来自 12 号。
>
> **v1.1-p0-fixed 变更**（2026-11-09 batch-275）：修完 batch-274 Leader verdict 的 7 条 P0：
> - M-2 §4.7 加 `version_task_run` 对账；
> - M-3 §4.8 加 `execution_job_id` 字段 + execution_job/plan_execution_job 关系说明；
> - M-4 §4.14 删 target_environments 新表，改为扩现有 `environment.py`；
> - M-5 §4.19 + §0 P0-5 明示 `ai_job / ai_shadow_run / ai_gateway_cache` 一并删；
> - M-16 §14 TestZeus AGPL 升级为法务书面评估硬门禁；
> - D-3 §4.12 加对象存储选型（dev 本地 FS / prod 三选一 TA-007 前定）；
> - D-9 §21.0 加 benchmark 数据集来源 + 准备进度。
>
> **v1.2-p1-fixed 变更**（2026-11-09 batch-276）：修完 batch-274 Leader verdict 的 12 条 P1（M-6/M-12/M-13/M-15/M-18/M-19/M-20/D-1/D-4/D-5/D-6/D-7）：
> - M-6 §4 + 附录 B.1 统一 project_id 隔离口径（Run 子表继承 `run.project_id`，全局表逐张明示）；
> - M-12 §24 ADR-AIQE-008 加 PR 模板强制问答（AITDE 翻版自检）；
> - M-13 §11.2 `UI_OVERLAY` 加 `requires_ui_surface: true` 元数据 + adapter capability 层声明启停；
> - M-15 §4.20 + §11.9 噪音规则 90 天上限可被 Owner 显式续期（续期另生成审计行）；
> - M-18 §14.4 PoC 矩阵加"失败回退方案"列；
> - M-19 §23 加 2-3 人团队放大线（MVP 16-20 周 / V1 32-40 周）；
> - M-20 §19 每条 TA 加"优先级档"列（MVP / V1 / V1.1+）；
> - D-1 §8.3 + 附录 C 按 DB 方言拆 seq 分配（SQLite 自增 + 唯一索引 / Postgres advisory lock）；
> - D-4 §16.2 定脱敏实现（复用 knowledge sanitize 正则 + YAML 规则表；presidio 为 V1.1+ 升级路径）；
> - D-5 §4.12 划清 `lanhu_evidence` 与 `run_artifacts` 边界（互不迁移，按 `linked_evidence_type` 并集查询）；
> - D-6 §18.2 前端路由决策（保留 `/version-tasks` 业务入口，新增 `/runs` 通用 Run 列表）；
> - D-7 §6.4 记录 `task_queue.py` 现状预检（无 advisory lock / 无独立 heartbeat 表 → TA-010.3 自实现）。
>
> **v1.3-baseline-aligned 变更**（2026-11-09 batch-278 决策回写）：TA-001 代码审计产出 [`docs/aiqe/baseline.md`](../aiqe/baseline.md)，用户确认 D-278-1..3 后回写本规格：
> - **D-278-1**：§4 关键规则改为"新建实体 UUID v4 / 跨接现有表的外键 BIGINT"（现有 73 表里 72 张是 INT 自增主键）；
> - **D-278-2**：§4.7 采用**候选 B** —— `version_task_run` 保留 + `test_run_id BIGINT` 回填，M2 后只读，V1.1 删表；
> - **D-278-3**：§18.2 前端目录改用现有 `pages/<domain>/`，不新建 `features/`；
> - 同步修正 4 处口径：模型 **43 文件 / 73 表**、目标表 **25 张（22 净新建 + 3 扩展）**、服务 **71 顶层 / 123 递归**、现有路由 **265 paths / 323 operations**；
> - §4.8 `node_runs.execution_job_id`、§4.7 `environment_id` 明确为 BIGINT；§15.2 标注 30 个端点中 29 个净新增。
>
> 剩余 13 条 P2 由后续批次陆续处理。

---

## 目录

- [§0 开工前置 P0（必须先修）](#0-开工前置-p0必须先修)
- [§1 产品定位与主链路](#1-产品定位与主链路)
- [§2 不做清单（吸取 AITDE 教训）](#2-不做清单吸取-aitde-教训)
- [§3 系统分层架构](#3-系统分层架构)
- [§4 数据模型（权威目标模型）](#4-数据模型权威目标模型)
- [§5 执行状态机](#5-执行状态机)
- [§6 Workflow DAG + 调度器](#6-workflow-dag--调度器)
- [§7 Driver 协议与注册表](#7-driver-协议与注册表)
- [§8 Run Event 协议与 SSE 订阅](#8-run-event-协议与-sse-订阅)
- [§9 Assertion 引擎（含 24 准则接线）](#9-assertion-引擎含-24-准则接线)
- [§10 Agent 服务与 Skill 开放标准](#10-agent-服务与-skill-开放标准)
- [§11 噪音与干扰因果治理](#11-噪音与干扰因果治理)
- [§12 缺陷闭环与一键回归](#12-缺陷闭环与一键回归)
- [§13 多端 Driver 与跨端对照](#13-多端-driver-与跨端对照)
- [§14 OSS 组件准入与评估](#14-oss-组件准入与评估)
- [§15 REST / MCP API 契约](#15-rest--mcp-api-契约)
- [§16 安全与数据治理](#16-安全与数据治理)
- [§17 项目适配器模板](#17-项目适配器模板)
- [§18 代码骨架与开发约定](#18-代码骨架与开发约定)
- [§19 阶段开发任务（TA-001 … TA-045）](#19-阶段开发任务ta-001--ta-045)
- [§20 E2E 验收场景（TC-AIQE-001 … 010）](#20-e2e-验收场景tc-aiqe-001--010)
- [§21 Agent 评估基准集](#21-agent-评估基准集)
- [§22 Definition of Done / 质量门禁](#22-definition-of-done--质量门禁)
- [§23 里程碑](#23-里程碑)
- [§24 ADR 清单](#24-adr-清单)
- [附录 A：开源组件版本锁](#附录-a开源组件版本锁)
- [附录 B：术语表](#附录-b术语表)
- [附录 C：Durability 分 DB 兼容表](#附录-cdurability-分-db-兼容表)


---

## §0 开工前置 P0（必须先修）

> 本章任何一条没完全通过，禁止进入 §19 的 Phase 1 开发。

| ID | 阻塞项 | 定位 | 开发要做的事 | 验收证据 |
|----|-------|------|-------------|---------|
| P0-1 | 生产 4 个 DeepSeek Key 实测全 401，ai-gateway 12 天零推理 | `work-logs/platform-simplification-production-eval-20261007.md` §3 | ① 轮换新 Key → 入 `production.env`；② `ai_config_service` 重连探测写 `ai_operation_records`；③ 真实发一次 `requirement→cases` LLM 调用 | `ai_operation_records` 新增一条 `status=success`；curl 返回 200 的 shell 记录入证据包 |
| P0-2 | 简化批次将 DROP 104 张表（不可逆） | 11 号 §2 | ① 跑一次完整备份恢复演练（复用 batch-262 脚本）；② 所有 DROP 迁移改用 `op.execute("DROP TABLE IF EXISTS ...")` 带存在性守卫；③ `alembic downgrade -1` 必须可逆 | 备份→恢复→抽行一致；`alembic upgrade head && alembic downgrade -1 && alembic upgrade head` 可执行 |
| P0-3 | 生产磁盘 96% | 11 号 §5 | 清理冷数据 + 扩盘；盘水位告警确认已送达 | 水位 ≤ 80% 维持 48 小时；告警平台收条 |
| P0-4 | `/uitest` 控制面内置浏览器（C263-1） | `services/ui_test_service.py` | 把 `playwright_executor` 的内置浏览器路径从控制面剥离，走 `cameltv-node`。**batch-277b-1 已落地代码侧**：新增 `uitest_execution_mode=node`（默认 `local`）→ `ExecutionJob(kind="ui")` 派发（`app/services/ui_job_dispatch.py` + `ui_test_run.execution_job_id`），节点侧新增 `run_spec_files` 执行 Playwright spec 并按 sha256 回传证据；**277b-2 待做**：真机节点验收 → 默认切 node → 控制面 Dockerfile 去 Chromium | 控制面镜像 `docker image inspect` 验证无 Chromium；`/uitest` 执行走 node；P0-4 evidence JSON |
| P0-5 | `app/services/ai_gateway/` + 相关 models 残留清理（batch-275 M-5 扩写） | 11 号 §6 D2 已决策 | **batch-277 已执行（代码侧）**：删除 `app/services/ai_gateway/`（8 文件）+ `app/models/ai_job.py`（`AiAgent` 迁移为 `app/models/execution_node.py::ExecutionNode`，表 `ai_agents` 保留为节点注册表）+ `ai_shadow_run.py` + `ai_gateway_cache.py`；新增 migration `20261109_b277_drop_retired_tables`（`DROP TABLE IF EXISTS` + downgrade 可重建）；`ai_client` 直连、嵌入本地化；`docs/ai/local-ai-agent.md` 重写、`scripts/ai_agent/` 删除、ADR-0027/0028/0029 标 `superseded` | `rg "ai_gateway\|AiJob\|AiShadowRun\|AiGatewayCache" test-platform-v2/backend/{app,tests,scripts}` 命中 0（历史 migration 除外）；`alembic upgrade head → downgrade -1 → upgrade head` 退出码 0；3 个 ADR `status: superseded`；文档已重写 |

> **2026-11-10 M1 完成**：batch-279（TA-005 Run 模型/状态机）、batch-280（TA-006 Event/Outbox）、batch-281（TA-007 Artifact）与 batch-282（TA-008 Run Console + 只读 API）全部开发完成并合入 main；新增 7 表（test_runs / node_runs / step_attempts / run_assertion_results / run_events / event_outbox / run_artifacts）、5 个只读 API、/runs 前端；后端 1398 passed / 43 skipped、前端 550 tests、ratchet PASS。生产迁移（20261111..13）留窗口执行；M2 可启动（TA-009 Workflow Validator / TA-010 DAG Scheduler）。收口报告：`work-logs/M1-phase1-closeout.md`。

> **2026-11-10 M2 进度**：batch-283（TA-009 Workflow Validator）已完成——覆盖环/悬空依赖/未注册 driver/悬空变量/非幂等重试/断言 expected/edges 一致性，并附 canonical checksum；16 单测；batch-284（TA-010 DAG Scheduler + TA-010.3 资源锁）已完成——workflow_definitions / resource_locks 两表、调度/并行/fail_fast/恢复、15 单测；全量 1429 passed。生产 20261114 两表待窗口部署；遗留项见 `work-logs/M1-M2-leftovers.md`；batch-285 已补 MinIO 自托管 Artifact 后端（已上线：容器 + 桶 + put/read 冒烟通过）；batch-286（TA-011 RunContext）已完成：变量解析/secret 脱敏/Run 隔离/调度器输出写入。batch-287（TA-012 HTTP Driver）已完成：真实 httpx 链、request/response 证据脱敏截断、首失败保留、超时映射。batch-288（TA-013 Playwright Driver）已完成：登录组合动作 + DOM/A11y/console/screenshot/trace 证据（sha256）。

> **2026-11-09 batch-277 状态（已完成）**：P0-1..5 全部 pass。P0-1 生产 3 条 provider 换新 Key，平台 `ai_client` 真实调用返回 OK；P0-2 备份演练 + DROP 守卫（downgrade 可执行）；P0-3 磁盘 87%→77%（用户豁免 48h，cron 每小时记录）；P0-4 控制面镜像无 Chromium，生产 `/uitest` 由节点执行（run 481，1/1 pass）；P0-5 ai_gateway 容器已停止删除、代码零残留。生产 2026-11-09 23:49 完成 104 表 DROP 迁移（alembic head `20261110_b277b_ui_run_exec_job`，public 表 94），部署前备份 `pre-deploy-20261109-233841.dump`。

**门禁**：上述 5 条全部拿到真实证据并入 PR 之前，`§19 Phase 1` 的 CI 守卫（`scripts/ci/check-p0-ready.ps1`，TA-001.5 产出）直接 fail-closed。


---

## §1 产品定位与主链路

### 1.1 一句话定位

**CamelTv AIQE = AI 版本验收工作台**：需求 → AI 生成计划 → 人审 → DAG 执行 → 证据沉淀 → 失败归因 → 缺陷 → 发布判定 → 版本知识 → 下一个版本复用。

- AI 只负责 **理解、规划、建议、证据分析**。
- 确定性 Runtime 负责 **状态、调度、工具执行、断言、权限**。
- 人负责 **需求冻结、未知偏差、高风险动作、发布决策**。

### 1.2 主链路图

```text
Requirement (v) ──► RequirementContract (frozen) ──► AcceptanceCriterion
         │                                                │
         ▼                                                ▼
   (A1 Requirement Agent)                        TestScenario (v) ──► TestCase (v)
                                                          │
                                        (A2 Test Design Agent 增强 24 准则 + 项目 Oracle)
                                                          │
                                                          ▼
                                              WorkflowDefinition (approved, checksum)
                                                          │
                                                 (A3 Workflow Planner + Validator)
                                                          │
                                                          ▼
                                     ExecutionProfile (core_isolated / integration / external_live)
                                                          │
                                                          ▼
                                                      TestRun
                                                          │
                                           ┌──────────────┼──────────────────────┐
                                           ▼              ▼                      ▼
                                       NodeRun (DAG)   RunEvent (append-only)  RunArtifact
                                           │
                                     StepAttempt ── AssertionResult
                                           │
                                 (若失败) A4 Failure & Interference Triage
                                           │
                            InterferenceObservation + TriageCase + TriageHypothesis
                                           │
                                 Counterfactual Replay (E1..E6)
                                           │
                                     ┌─────┴─────┐
                                     ▼           ▼
                                  Defect ───► RegressionRequest ──► new TestRun
                                                                     (retest_of, diff)
                                     │
                              VersionTask Quality Gate
                                     │
                              ReleaseBundle (PASS/CONDITIONAL/REJECT)
                                     │
                              A6 Learning Curator ──► LearningCandidate ──► BugPattern (approved)
```

### 1.3 关键边界（三个必须分清楚的概念）

| 概念 | 是什么 | 不是什么 |
|------|-------|---------|
| `ExecutionJob` | 节点派发的工作单元（现有） | **不是**测试场景定义 |
| `WorkflowDefinition` | 已批准的 DAG + 变量绑定 + 断言 | **不是**一次执行；**不是**Agent 的临时任务图 |
| `TestRun` | 一次具体执行实例 | **不是**用例、**不是** Workflow |

### 1.4 AI 与 Runtime 的分工边界

- AI 可做：规划草案、歧义识别、覆盖补全建议、失败多假设、噪音归因建议、learning candidate。
- AI 不可做：
  - 不可覆盖 `Runtime` 给出的 `execution_outcome`；
  - 不可直接发任意 HTTP/SQL/Shell/文件写操作；
  - 不可无证据下断言 PASS/FAIL；
  - 不可静默修改已审核脚本或已冻结 Workflow；
  - 不可自动关闭缺陷。


---

## §2 不做清单（吸取 AITDE 教训）

> 2026-10-07 评估：AITDE 180 文件 22.9k 行、30+ 批次，生产 0 真实 Run。本章把教训明文化，任何 PR 引入下列任一项必须被拒。

1. ❌ **不建第二套 Mission / Contract / Scenario / Oracle 平行建模实体**。本文的 `TestScenario / RequirementContract / WorkflowDefinition` 是**唯一**建模层；禁止平行再造。
2. ❌ **不建 Temporal / 自研 Durable Runtime**。第一阶段复用 `ExecutionJob + task_queue.py` + DB 事务 + Alembic；只有确认故障恢复/超大规模确有需要再评估。
3. ❌ **不写"planner stub + executor echo"**。任何 Agent PR 的验收要有真实 Run 证据，不能是模拟数据。
4. ❌ **不加"AI Gateway / Local Inference / Shadow Mode"抽象层**。`ai_client` 直连 LLM provider。
5. ❌ **不建第二套用例体系**。同一张表，字段 `source_json.generated_by=ai` 标明来源即可。
6. ❌ **不用用例数量作为 KPI**。遵守 04 号 foolproof 禁令。
7. ❌ **不做"fine-tune 内部 QA 模型"**。prompt + skill 足够。
8. ❌ **不在控制面跑浏览器 / 模型推理 / ffmpeg**。P0-4 已明确收口 `/uitest` 内置浏览器。
9. ❌ **不写"AI 自证"脚本**（AI 自己生成 + 自己跑 + 自己判 PASS）。
10. ❌ **不在生产环境做任何写操作**。只读走 `assert_public_url()` + 支付红线。
11. ❌ **不让 LLM 临场决定已批准 Workflow 的每一步**。LLM 只做有限的语义动作（探索模式），正式回归用确定性脚本 + 断言。
12. ❌ **不把"用例总数增长"作为增强效果证明**。用缺陷捕获率、覆盖率、漏测率衡量。
13. ❌ **不恢复旧 AITDE/DSH/知识图谱/报告中心/测试数据集/通知集成/组织管理/主题实验室 等已删模块**（11 号方案已定）。
14. ❌ **不让第三方工具成为 Run/Defect/Requirement 的事实源**。CamelTv DB 是唯一真相源；ReportPortal/Allure 是可选投影。
15. ❌ **不让 UI 文案暴露 Scenario/Oracle/Contract 等引擎术语**（03 号术语图规则）。


---

## §3 系统分层架构

```text
┌───────────────────────────────────────────────────────────────────────────────┐
│ Layer 5：Clients                                                                │
│   React Console  │  CLI  │  CI (Jenkins/GitHub Actions)  │  MCP Clients         │
│                                                            (Codex/Claude/Cursor) │
├───────────────────────────────────────────────────────────────────────────────┤
│ Layer 4：Gateway                                                                │
│   REST API (/api/v1/*)  │  MCP Gateway  │  OpenAPI generator                   │
├───────────────────────────────────────────────────────────────────────────────┤
│ Layer 3：Existing FastAPI app / RBAC / Project Context / Audit                 │
├───────────────────────────────────────────────────────────────────────────────┤
│ Layer 2：AIQE Core                                                              │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐                 │
│  │ Agent Service   │  │ Workflow /      │  │ Noise /         │                 │
│  │ (A0..A6)        │  │ DAG Scheduler   │  │ Triage Engine   │                 │
│  │ typed contracts │  │ RunContext      │  │ Counterfactual  │                 │
│  │ tool allowlist  │  │ Variable Store  │  │ Replay          │                 │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘                 │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐                 │
│  │ Event Collector │  │ Artifact Mgr    │  │ Assertion Engine│                 │
│  │ Outbox+SSE      │  │ sha256+redact   │  │ 24 rules + DSL  │                 │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘                 │
├───────────────────────────────────────────────────────────────────────────────┤
│ Layer 1：Driver Registry + ExecutionJob Dispatcher                              │
│   httpx  │ playwright │ db-ro │ event │ mobile │ miniapp │ device │ external   │
├───────────────────────────────────────────────────────────────────────────────┤
│ Layer 0：cameltv-node (本地执行节点，装 OSS Agent 作为能力)                      │
│   Playwright 1.56 + Agents │ Midscene.js │ Appium MCP │ browser-use │ minium   │
│   + Secret Vault ref / Egress allowlist / H1..H5                               │
└───────────────────────────────────────────────────────────────────────────────┘
```

### 3.1 控制面硬约束（H1-H5，继承 09 号）

- **H1 执行沙箱**：节点进程非 root；无平台 secret；egress 白名单；静态拦截 `child_process/fs/net/process.env`。
- **H2 `assert_public_url()`**：生产只读 URL 强校验。
- **H3 凭据最小化**：被测系统凭据只在节点 `.env`（chmod 600），控制面不存。
- **H4 证据防篡改**：bundle manifest sha256，发布判定绑定 bundle hash。
- **H5 节点 token 可吊销**。
- 新增规则：任何从用户输入到网络/磁盘/代码执行的新路径，必须附带 guard + 回归测试。

### 3.2 五个事实源

- `TestRun / NodeRun / StepAttempt / AssertionResult / RunEvent / RunArtifact` 的 **CamelTv DB** 是唯一事实源。
- ReportPortal / Allure 结果只做 **投影**，不反向写回。
- 第三方 Agent 的 locator 修复只能生成**草案**，不能静默改已审核脚本。


---

## §4 数据模型（权威目标模型）

> 本章是**权威目标模型**。所有表由 Alembic 迁移产出。
> **关键规则**：
> - 所有 JSON 字段必须有 Pydantic Schema + `schema_version`，schema 冲突由 CI 守卫（TA-004.2）拒 PR。
> - **Project 隔离**（batch-276 M-6，细则唯一出处见 **附录 B.1**）：业务主表必须带 `project_id`；Run 子表（`node_runs / step_attempts / assertion_results / run_events / event_outbox / run_artifacts / interference_observations / triage_cases / triage_hypotheses / regression_requests`）**不重复存 `project_id`**，一律继承 `run.project_id`，查询必须 join `test_runs` 并带 project 过滤；`test_cases` 经 `test_scenarios` 继承；全局表（`node_capability_manifests / learning_candidates / bug_patterns` 等）在附录 B.1 逐张明示。
> - 所有时间字段使用 **naive UTC**（`datetime.now(UTC).replace(tzinfo=None)`，与 `app/core/task_queue.py::utcnow` 一致；PG 列可用 `timestamptz`，SQLite 天然 naive）。batch-278 C-02。
> - **ID 类型**（batch-278 D-278-1）：**新建实体一律 `UUID v4`**；**跨接现有表的外键一律 `BIGINT`**（现有 73 张表里 72 张为 `INTEGER` 自增主键，仅 `ai_task` 为 str；详见 [`docs/aiqe/baseline.md`](../aiqe/baseline.md) C-01）。新表 ↔ 新表用 UUID。
> - **JSON 类型**（batch-278 C-03）：新表用 `sa.JSON`（SQLite 存 TEXT / PG 存 jsonb）；现有 `*_json` 为 `Mapped[str]` 的旧表**不做类型迁移**。
> - **规模口径**（batch-278）：本章 **25 张表（22 净新建 + 3 扩展）**，对照现有 **43 个模型文件 / 73 张表**；完整对账见 [`docs/aiqe/baseline.md`](../aiqe/baseline.md)。
> - **写之前必须完成 TA-001 代码审计**：若现有 SQLAlchemy Model 已有同义实体，优先 ALTER 扩展，不新建。

### 4.1 实体关系总图

```text
Requirement ──► RequirementContract ──► AcceptanceCriterion
                       │
                       ▼
                 TestScenario ──► TestCase
                                     │
                       WorkflowDefinition
                                     │
                                  TestRun ──► NodeRun ──► StepAttempt ──► AssertionResult
                                     │             │             │
                                     ▼             ▼             ▼
                                 RunEvent     RunArtifact   InterferenceObservation
                                     │                             │
                                     ▼                             ▼
                              EventOutbox                     TriageCase ──► TriageHypothesis
                                                                   │
                                                                   ▼
                                                              Defect ──► RegressionRequest
                                                                             │
                                                                             ▼
                                                                           TestRun (retest_of)
                                     
AgentExecution  (任意 Agent 调用审计)
LearningCandidate ──► BugPattern (approved)
ExecutionProfile  (Run 启动前选择)
Environment (扩展现有 environment 表，见 §4.14)
NodeCapabilityManifest (节点自描述)
NoiseSuppressionRule (已知干扰规则)
ProjectAdapter (多项目支持)
```

### 4.2 `requirement_contracts`

| 字段 | 类型 | 约束 |
|-----|------|------|
| id | UUID | PK |
| project_id | FK | NOT NULL |
| requirement_id | FK | NOT NULL |
| version | integer | NOT NULL；同 requirement 内唯一 |
| source_docs_json | JSON | PRD/原型/会议纪要 refs，每条含 `{type, path, sha256, line_range?}` |
| intent | text | 业务测试意图 |
| business_rules_json | JSON | `[{rule_key, text, source_refs[]}]` |
| open_questions_json | JSON | `[{question, risk, blocking}]` |
| conflicts_json | JSON | 来源之间的矛盾 |
| checksum | varchar(128) | 规范化 JSON hash；冻结后不变 |
| approval_status | enum | `draft / pending / approved / rejected` |
| approved_by | FK users | nullable |
| approved_at | timestamp | nullable |
| created_at / updated_at | timestamp | 审计 |

唯一索引：`(requirement_id, version)`。

### 4.3 `acceptance_criteria`

| 字段 | 类型 | 说明 |
|-----|------|------|
| id | UUID | PK |
| contract_id | FK | 所属契约 |
| ac_key | varchar(100) | 契约内唯一，如 `AC-FAV-001` |
| given_json | JSON | 前置条件（结构化） |
| when_action | varchar(255) | 触发动作 key |
| then_json | JSON | 可观测结果列表，每条 `{observable_check, expected}` |
| platforms_json | JSON | `["web","mobile_web","android",...]` |
| source_refs_json | JSON | 必须能回到契约里的章节/行 |
| ambiguity | enum | `none / low / medium / high` |
| derived | boolean | AI 推导必须 true |
| created_at | timestamp | — |

**强制规则**：`derived=true` 的 AC 必须被人工显式确认才能进入 scenario 生成。

### 4.4 `test_scenarios`

| 字段 | 类型 | 说明 |
|-----|------|------|
| id | UUID | PK |
| project_id | FK | — |
| scenario_key | varchar(100) | 项目内唯一 |
| title | varchar(255) | — |
| intent | text | — |
| contract_version_id | FK | 冻结契约版本 |
| risk_level | enum | `P0/P1/P2/P3` |
| status | enum | `draft / reviewed / approved / deprecated` |
| version | integer | — |
| created_by / created_at / updated_at | FK/ts | 审计 |

唯一索引：`(project_id, scenario_key, version)`。

### 4.5 `test_cases`

| 字段 | 类型 | 说明 |
|-----|------|------|
| id | UUID | PK |
| scenario_id | FK | — |
| case_key | varchar(100) | 人类可读唯一编号 |
| title | varchar(255) | — |
| case_type | enum | `functional / api / ui / integration / data / contract / performance / security / manual` |
| priority | enum | `P0/P1/P2/P3` |
| preconditions_json | JSON | 登录、数据、系统状态 |
| data_plan_json | JSON | fixture 引用，**不存密钥** |
| steps_json | JSON | 结构化 TestStep |
| assertions_json | JSON | 结构化断言（见 §9） |
| platform_bindings_json | JSON | `[{platform_key, driver, workflow_ref, enabled}]` |
| dependencies_json | JSON | 依赖 scenario/case/fixture |
| cleanup_json | JSON | 清理策略 |
| automation_level | enum | `manual / assisted / deterministic / agentic` |
| review_status | enum | `draft / needs_review / approved / rejected` |
| version | integer | 不覆盖已发布版本 |
| source_json | JSON | `{generated_by: "ai" \| "human", rule_refs: [...], bug_pattern_refs: [...]}` |
| schema_version | varchar(20) | case JSON schema |
| created_at / updated_at | timestamp | — |


### 4.6 `workflow_definitions`

| 字段 | 类型 | 说明 |
|-----|------|------|
| id | UUID | PK |
| project_id | FK | — |
| scenario_id | FK | 来源场景 |
| version | integer | — |
| graph_json | JSON | nodes + edges + bindings（见 §6） |
| schema_version | varchar(20) | graph schema |
| checksum | varchar(128) | 规范化 JSON hash；approved 后不变 |
| validation_status | enum | `draft / valid / invalid` |
| approval_status | enum | `pending / approved / rejected` |
| approved_by | FK | nullable |
| approved_at | timestamp | nullable |
| created_at | timestamp | — |

唯一索引：`(scenario_id, version)`。
写入规则：approval_status 转 `approved` 后，graph_json/checksum 不可再改；修改必须新建 version。

### 4.7 `test_runs`

| 字段 | 类型 | 说明 |
|-----|------|------|
| id | UUID | PK |
| project_id | BIGINT FK | 指向现有 `sys_project.id`（INT，batch-278 D-278-1） |
| run_key | varchar(100) | 可读执行编号 `RUN-YYYYMMDD-NNNNN` |
| source_type | enum | `manual / version_task / defect_regression / pr / github_action / schedule / agent` |
| source_id | UUID/string | nullable；指向触发源（`version_task` 来源为旧表 INT，存字符串或加 `legacy_task_id BIGINT`） |
| scenario_id | UUID FK | nullable；指向 `test_scenarios` |
| workflow_definition_id | UUID FK | 冻结 Workflow |
| build_ref | varchar(255) | build/version |
| commit_sha | varchar(64) | 被测代码 SHA |
| environment_id | BIGINT FK environments | 现有 `environment.id`（INT） |
| execution_profile_id | UUID FK | 指向 `execution_profiles` |
| environment_snapshot_json | JSON | 浏览器/服务版本/flags/地区/时间/依赖健康 |
| retest_of | UUID FK test_runs | nullable；回归指向被回归的 run |
| status | enum | `DRAFT / VALIDATING / QUEUED / RUNNING / WAITING_HUMAN / TRIAGING / COMPLETED / BLOCKED / CANCELED / ERROR` |
| outcome | enum | nullable；`PASS / FAIL / INCOMPLETE / UNKNOWN`（仅 COMPLETED 时写） |
| trigger_user_id | BIGINT FK | nullable；现有 `sys_user.id` |
| started_at / finished_at | timestamp | nullable |
| duration_ms | bigint | nullable |
| created_at | timestamp | — |

索引：`(project_id, created_at desc)`、`(scenario_id, created_at desc)`、`(commit_sha)`、`(retest_of)`。
**关键规则**：`status` 和 `outcome` 独立，`BLOCKED / CANCELED` 永远不算 PASS。

**与现有 `version_task_run.py` 的关系**（batch-275 M-2 补充）：

现有 `app/models/version_task_run.py` 承接"版本任务的一次执行"。本规格 `test_runs` 是**通用执行实例**，`version_task_run` 为其**派生场景**（`source_type = 'version_task'` 的 `test_runs`）。

**迁移策略**（batch-278 D-278-2 **已定案：候选 B**）：

- `version_task_run` **保留**，新增 `test_run_id BIGINT`（nullable）指向 `test_runs.id`；`test_runs` 是事实源，旧表是兼容关联；
- **M1-M2 双写**：版本任务执行时同时写 `test_runs(source_type='version_task')` 与旧 `version_task_run`，并回填 `test_run_id`；
- **M2 结束后旧表只读**（历史查询走 join）；**V1.1 删表**，删除前 `test_run_id` 回填率必须 100%（C-278-2）；
- **不采用候选 A**（直接 ALTER 并入）：会同时改版本任务前端 + `version_task_service` / `version_task_exec_service` / `execution_job_service` 三处，M1 风险不可接受。

本规格的 `test_runs` 字段表以通用执行实例为准，开发时**不得**创建与 `version_task_run` 字段完全重复的新表。

### 4.8 `node_runs`

| 字段 | 类型 | 说明 |
|-----|------|------|
| id | UUID | PK |
| run_id | UUID FK test_runs | — |
| node_key | varchar(100) | Workflow 节点 key |
| driver_key | varchar(80) | `http / playwright / db / event / mobile / miniapp / device / external_e2e` |
| worker_id | varchar(128) | nullable；执行节点 |
| status | enum | `PENDING / READY / QUEUED / RUNNING / WAITING / PASSED / FAILED / BLOCKED / SKIPPED / CANCELED / ERROR` |
| input_ref | JSON | 脱敏或加密变量引用 |
| output_ref | JSON | 变量名 → JSONPath/Artifact ref |
| error_class | varchar(80) | nullable |
| resource_keys_json | JSON | 占用锁 keys（见 §6） |
| execution_job_id | BIGINT FK execution_jobs | nullable；一对一关联调度派发工作单元（现有 `app/models/execution_job.py`，INT 主键） |
| started_at / finished_at | timestamp | — |
| attempt_count | integer | — |

唯一索引：`(run_id, node_key)`。

**与现有 `execution_job.py / plan_execution_job.py` 的关系**（batch-275 M-3 补充）：

- `execution_jobs` 是**派发工作单元**（现有）：承载"节点侧要做什么、给哪个 worker"；
- `node_runs` 是 **DAG 节点执行事实**（本规格新增）：承载"这个节点现在跑到哪一步、结果是什么"；
- 二者 **1:1 绑定**。创建 `node_runs` 时若尚未派发，`execution_job_id = null`；派发后回填。
- `plan_execution_job` 是旧的"测试计划执行派发"。11 号方案 §2 已声明"老队列 `api_task_worker` 和 `plan_execution_queue` 删除"；若 `plan_execution_job` 属于该队列则 **在 batch-277 清 P0 时一并核实并删除**；若否 → 作为 `execution_job` 的历史别名保留，不参与新 DAG。

### 4.9 `step_attempts`

| 字段 | 类型 | 说明 |
|-----|------|------|
| id | UUID | PK |
| node_run_id | FK | — |
| step_key | varchar(100) | — |
| attempt_no | integer | 从 1 开始 |
| status | enum | `QUEUED / RUNNING / PASSED / FAILED / BLOCKED / TIMED_OUT / CANCELED / ERROR` |
| started_at / finished_at | timestamp | — |
| input_summary_json | JSON | 脱敏输入摘要 |
| output_summary_json | JSON | 输出摘要 |
| error_json | JSON | nullable；`{class, message, stack_ref, severity}` |
| external_execution_ref | varchar(255) | nullable；外部执行器 ID |

唯一索引：`(node_run_id, step_key, attempt_no)`。
**关键规则**：Attempt 永久保留；重试成功不删除失败 Attempt。

### 4.10 `assertion_results`

| 字段 | 类型 | 说明 |
|-----|------|------|
| id | UUID | PK |
| step_attempt_id | FK | — |
| assertion_key | varchar(100) | — |
| assertion_type | enum | `value / schema / visual / state / business / db / event / performance / interaction_rule`（后者绑 24 准则 A01-A24） |
| rule_id | varchar(40) | nullable；`A01-A24` 或项目扩展 |
| status | enum | `PASS / FAIL / NOT_EVALUATED / ERROR` |
| expected_json | JSON | — |
| actual_json | JSON | 必须脱敏 |
| diff_json | JSON | nullable |
| evidence_refs_json | JSON | Artifact IDs / Event seq |
| evaluated_by | enum | `deterministic / ai_assisted / human` |

> **batch-279（TA-005）落地决策**：
> - **D-279-1**：既有 `assertion_results` 属 AITDE `execution_runtime`（7654 行、INT id、schema 不同），新表命名 **`run_assertion_results`**，避免同名冲突；
> - **D-279-2**：`test_runs.scenario_id` 按现有 `test_scenarios.id`（INT）使用 **BIGINT 外键**，与本文件字段表的 UUID 假设不同（遵循“旧表外键 BIGINT”规则）；
> - **D-279-3**：初始迁移 `Base.metadata.create_all` 会在新库预建全量表，迁移检测到 M1 schema 已存在时跳过；
> - **D-279-5**：`workflow_definition_id / execution_profile_id` 在 M2 建表前不建 FK。
> 详见 `work-logs/batch-279-design.md`。

### 4.11 `run_events` + `event_outbox`

事件为 **append-only**。

**`run_events`**：

| 字段 | 类型 | 说明 |
|-----|------|------|
| id | UUID | PK |
| run_id | FK | — |
| seq | bigint | 单 Run 严格递增序号 |
| node_run_id | FK | nullable |
| step_attempt_id | FK | nullable |
| event_type | varchar(80) | — |
| occurred_at | timestamp | — |
| producer | varchar(80) | `api_runner / playwright / keploy / agent / system / node` |
| correlation_id | varchar(128) | nullable |
| payload_json | JSON | schema 验证 + 脱敏 |
| producer_event_id | varchar(128) | 节点侧幂等 key |

唯一索引：`(run_id, seq)`、`(run_id, producer_event_id)`。

**`event_outbox`**：

| 字段 | 类型 | 说明 |
|-----|------|------|
| id | bigint | PK autoincrement |
| run_event_id | FK | — |
| dispatched_at | timestamp | nullable |
| retry_count | integer | 默认 0 |
| last_error | text | nullable |

**事务规则**（TA-006）：`append_event()` 必须在**同一 DB 事务**内写 `run_events` + `event_outbox`，否则事件可能丢失。SSE/Redis PubSub 由 outbox dispatcher 推送，消费端按 `event_id` 去重。


> **batch-280（TA-006）落地决策**：
> - **D-280-1**：`event_outbox.id` 使用 `BigInteger().with_variant(Integer, "sqlite")`，PG 为 BIGINT、SQLite 走 rowid 自增；
> - **D-280-2**：迁移检测 `run_events.seq` 已存在则跳过（初始 `create_all` 预建）；
> - **D-280-3**：`payload_json` 运行时强制 **schema_version**，逐类 payload schema 在 M2 补齐（TA-004.2）；
> - **D-280-4**：幂等键为 `(run_id, producer_event_id)`，NULL 不参与去重。
> 详见 `work-logs/batch-280-design.md`。

### 4.12 `run_artifacts`

| 字段 | 类型 | 说明 |
|-----|------|------|
| id | UUID | PK |
| run_id | FK | — |
| node_run_id / step_attempt_id | FK | nullable |
| artifact_type | enum | `screenshot / video / trace / har / log / request / response / dom / a11y / report / db_snapshot / other` |
| storage_uri | text | 私有对象存储路径；不公开桶 URL |
| sha256 | varchar(64) | 完整性 |
| size_bytes | bigint | 限额 |
| mime_type | varchar(100) | — |
| redaction_status | enum | `pending / sanitized / rejected` |
| metadata_json | JSON | 浏览器/viewport/页码等 |
| linked_evidence_type | enum | nullable；跨源证据引用类型 `lanhu_evidence / defect / external_url`（batch-276 D-5） |
| linked_evidence_id | varchar(64) | nullable；与 `linked_evidence_type` 成对使用 |
| created_at | timestamp | — |

**对象存储选型**（batch-275 D-3 补充）：

- **dev 环境**：**本地文件系统**（`storage_uri = file://<data-dir>/artifacts/<sha256-prefix>/<sha256>`），默认目录 `test-platform-v2/backend/storage/artifacts/`；
- **test 环境**：同 dev，或走 docker volume；
- **production 环境**：候选三选一，由 **TA-007 开工前业务 PoC** 后定：
  - **A. 腾讯云 COS**（统一服务商；Server-Side Encryption + 签名 URL）；
  - **B. MinIO 自托管**（制品不出站 + 省钱；需多维护一个服务 + 磁盘容量规划）；
  - **C. 本地 FS**（延续 dev 做法；dogfood 跟不上生产水位）。

**TA-007 的 driver 接口必须屏蔽后端差异**（`ArtifactStorageBackend` 抽象）；选型变更不影响业务代码。

**与 `lanhu_evidence` 的证据边界**（batch-276 D-5）：

- `lanhu_evidence_job / page / asset / ocr_block`（现有 `app/models/lanhu_evidence.py`）承接**蓝湖专项证据包**（原型截图、页面树、OCR、Word/JSON 导出），检索键是 `project_id + doc_id/version_id`；
- `run_artifacts` 承接 **Run 执行证据**（截图 / trace / HAR / 日志 / 请求响应 / DB 快照），检索键是 `run_id`；
- **两者互不迁移**：不把蓝湖证据复制进 `run_artifacts`，也不把 Run 证据写进 `lanhu_evidence`；各自保留原始表结构与权限（均按 `project_id` RBAC）；
- 需要跨源引用时，在 `run_artifacts.linked_evidence_type + linked_evidence_id` 落引用（不复制文件），Evidence 聚合查询按 `linked_evidence_type` 做并集；
- TA-007 验收必须覆盖"一条 Run 的 Artifact 列表 + 它引用的蓝湖证据"能在同一 EvidenceBundle 视图中出现且权限一致。

> **batch-281（TA-007）落地决策**：
> - **D-281-1**：`storage_uri = file://<root>/<sha256[:2]>/<sha256[2:4]>/<sha256>`，内容寻址天然去重；
> - **D-281-2**：`settings.storage_dir` 未声明，用 `getattr(...,"storage")` 回退；
> - **D-281-3**：`redaction_status` 只允许 pending → sanitized / rejected；
> - **D-281-4**：生产 COS/MinIO 后端等 TA-007 PoC 选型，业务只依赖 `ArtifactStorageBackend`；
> - **D-281-5**：HTTP 上传/下载端点推迟到 batch-282 与 Console 联调。
> 详见 `work-logs/batch-281-design.md`。

### 4.13 `execution_profiles`

| 字段 | 类型 | 说明 |
|-----|------|------|
| id | UUID | PK |
| project_id | FK | — |
| name | varchar(100) | — |
| purpose | enum | `core_isolated / integration / external_live` |
| config_json | JSON | feature flags / 外部依赖 mode / 网络路由 / 浏览器矩阵 / 数据 namespace / 固定时钟 / locale 与 timezone / 广告弹窗插件开关 / 请求记录策略 |
| version | integer | — |
| checksum | varchar(128) | — |
| approval_status | enum | — |
| owner_id | FK | — |
| expires_at | timestamp | nullable |
| created_at | timestamp | — |

密钥只能是 Vault / env var 引用。

### 4.14 `environments`（**扩现有 `environment.py`**，不新建表）

**batch-275 M-4 修正**：原 §4.14 提议新建 `target_environments` 表，与现有 `app/models/environment.py` 字段完全重复。改为**扩展现有表**，不新建。

**扩展规则**：在现有 `environments` 基础上新增以下字段：

| 字段 | 类型 | 说明 |
|-----|------|------|
| base_urls_json | JSON | `{admin, consumer_web, consumer_h5, api}` 多端 base URL |
| data_sources_json | JSON | DB/Redis/MongoDB/Kafka 连接 slot（env var ref） |
| build_check_endpoint | varchar(500) | 健康检查 URL |
| allowed_actions | enum | `read_only / limited_write / full_write` |

现有 `environments` 的所有字段（`id / name / project_id / 鉴权 slot` 等）保留不变。

**迁移策略**（Alembic）：

- `op.add_column('environments', sa.Column('base_urls_json', postgresql.JSONB, nullable=True))` × 4 字段；
- 老数据 `base_urls_json` 从 `name` 推断或人工补；
- `allowed_actions` 默认 `read_only`，production 环境显式升为 `limited_write`。

**全文引用约定**：本规格其他章节出现 `target_environment_id` 均等价于 `environment_id`（引用 `environments.id`）。

### 4.15 `interference_observations`

| 字段 | 类型 | 说明 |
|-----|------|------|
| id | UUID | PK |
| run_id | FK | — |
| node_run_id / step_attempt_id | FK | nullable |
| category | enum | `ENVIRONMENT / TEST_DATA / CONCURRENCY / THIRD_PARTY / NETWORK / TIME / CROSS_FEATURE / UI_OVERLAY / AUTOMATION / REQUIREMENT_AMBIGUITY / UNKNOWN` |
| signal_type | varchar(80) | — |
| signal_payload_json | JSON | 原始信号脱敏后 |
| evidence_refs_json | JSON | — |
| observed_at | timestamp | — |
| correlation_id | varchar(128) | nullable |
| source | enum | `detector / agent / human` |
| is_controlled | boolean | 是否已采取控制措施 |
| control_action | varchar(255) | nullable |
| control_result | varchar(100) | nullable |
| created_by | FK/varchar | — |

### 4.16 `triage_cases` / `triage_hypotheses`

**`triage_cases`**：

| 字段 | 类型 | 说明 |
|-----|------|------|
| id | UUID | PK |
| run_id | FK | — |
| primary_node_run_id | FK | — |
| status | enum | `open / investigating / needs_human / resolved` |
| primary_classification | enum | `PRODUCT_DEFECT / CROSS_FEATURE_DEFECT / ENVIRONMENT / TEST_DATA / CONCURRENCY / THIRD_PARTY / NETWORK / TIME / AUTOMATION / REQUIREMENT_GAP / FLAKY / UNKNOWN` |
| product_scope | enum | `inside_scope / cross_feature / external / unknown` |
| evidence_completeness | enum | `insufficient / partial / sufficient` |
| created_at / resolved_at | timestamp | — |
| resolved_by | FK | nullable |

**`triage_hypotheses`**：

| 字段 | 类型 | 说明 |
|-----|------|------|
| id | UUID | PK |
| triage_case_id | FK | — |
| hypothesis_key | varchar(100) | — |
| classification | enum | 同上 |
| explanation | text | — |
| supporting_evidence_json | JSON | — |
| contradicting_evidence_json | JSON | — |
| missing_evidence_json | JSON | — |
| proposed_experiment_json | JSON | E1-E6 任一（见 §11.4） |
| confidence_calibration_version | varchar(40) | nullable |
| rank | integer | — |
| verification_status | enum | `proposed / confirmed / rejected / unverified` |
| verification_run_id | FK test_runs | nullable |

一条失败**可以有多个假设**，不允许只存一个"AI 原因"。

### 4.17 `defects`

| 字段 | 类型 | 说明 |
|-----|------|------|
| id | UUID | PK |
| project_id | FK | — |
| title | varchar(255) | — |
| severity | enum | `P0/P1/P2/P3` |
| status | enum | `open / confirmed / fixing / pending_review / closed / rejected` |
| assignee | FK | nullable |
| creator | FK | — |
| linked_case_id | FK test_cases | nullable |
| linked_execution_id | FK test_runs | nullable |
| linked_ac_id | FK | nullable |
| triage_case_id | FK | nullable |
| steps_to_reproduce_json | JSON | 结构化：`[{seq, action, data}]` |
| expected | text | — |
| actual | text | — |
| environment_snapshot_json | JSON | 复用 run 的快照 |
| fixed_commit_sha | varchar(64) | nullable |
| external_id | varchar(255) | nullable（Jira/TAPD） |
| created_at / updated_at | timestamp | — |

状态流（现有基础上扩展）：

```text
open ─► confirmed ─► fixing ─► pending_review ─► closed
  │         │                       │
  ├─► rejected                      └─► fixing（回归失败）
```

### 4.18 `regression_requests`

| 字段 | 类型 | 说明 |
|-----|------|------|
| id | UUID | PK |
| defect_id | FK | — |
| source_run_id | FK | — |
| fixed_commit_sha | varchar(64) | — |
| selection_mode | enum | `failed_cases / scenario / impact_set / p0_smoke / custom` |
| selected_case_ids_json | JSON | — |
| status | enum | `pending / validating / running / completed / failed` |
| new_run_id | FK | nullable |
| requested_by / approved_by | FK | — |
| created_at / completed_at | timestamp | — |

### 4.19 `agent_executions` / `learning_candidates` / `bug_patterns`

**与已删 `ai_job / ai_shadow_run / ai_gateway_cache` 的关系**（batch-275 M-5 补充）：

这三张表承载的"shadow run 对比 / gateway cache / job 分发"等能力**在 11 号简化批次 + batch-277 P0-5 一并删除**。`agent_executions` 单独承载所有 Agent 调用审计，**不恢复**旧字段。旧数据如需追溯归档至 `work-logs/platform-simplification-production-eval-20261007.md`。

**`agent_executions`**（Agent 审计；**全局表**：`project_id` nullable，按调用方项目写入但不强制隔离，见附录 B.1）：

| 字段 | 类型 | 说明 |
|-----|------|------|
| id | UUID | PK |
| project_id | FK | nullable |
| agent_key | varchar(100) | A0..A6 |
| agent_version | varchar(40) | `{prompt_version}-{schema_version}-{tools_version}-{model_version}` |
| actor_id | FK users | — |
| task_type | varchar(80) | `requirement_analysis / case_design / workflow_plan / triage / impact / learning_candidate` |
| provider / model | varchar(80) | — |
| prompt_version | varchar(40) | — |
| input_ref | text | artifact ref / 文件 URI |
| output_ref | text | — |
| tool_calls_json | JSON | 工具白名单调用链 |
| token_usage_json | JSON | `{prompt, completion, total, cost_cny}` |
| status | enum | `succeeded / needs_human / failed / canceled` |
| error_json | JSON | nullable |
| started_at / finished_at | timestamp | — |

**所有 AI 调用必须写一行**（P0-1 已校准的规则）。

**`learning_candidates`**：

| 字段 | 类型 | 说明 |
|-----|------|------|
| id | UUID | PK |
| source_type | enum | `confirmed_defect / production_incident / human_input` |
| source_ref | varchar(255) | — |
| candidate_rule_json | JSON | 候选规则（含 detection_point / trigger_signature / test_oracle） |
| applicable_scope_json | JSON | `{projects: [...], domains: [...], platform_versions: [...]}` |
| counter_examples_json | JSON | — |
| benchmark_result_json | JSON | 评估集跑分 |
| status | enum | `CANDIDATE / EVALUATING / REVIEW_REQUIRED / APPROVED / ACTIVE / DEPRECATED / ROLLED_BACK` |
| approved_by | FK | nullable |
| version | integer | — |
| effective_from / expires_at | timestamp | — |
| created_at | timestamp | — |

**`bug_patterns`**（只有 approved 的才能进）：

| 字段 | 类型 | 说明 |
|-----|------|------|
| id | UUID | PK |
| pattern_key | varchar(100) | 项目内唯一 |
| detection_point | text | — |
| trigger_signature | text | — |
| test_oracle | text | — |
| applicable_scope_json | JSON | — |
| learning_candidate_id | FK | — |
| version | integer | — |
| status | enum | `active / deprecated` |

### 4.20 `noise_suppression_rules`

| 字段 | 类型 | 说明 |
|-----|------|------|
| id | UUID | PK |
| scope | enum | `project / environment / profile / case / dependency` |
| scope_ref | varchar(255) | — |
| category | enum | 同 interference 分类 |
| match_condition_json | JSON | `{fingerprint?, step_regex?, error_regex?}` |
| effective_from / effective_until | timestamp | — |
| owner_id | FK | — |
| reason | text | — |
| linked_issue_ref | varchar(255) | — |
| evidence_refs_json | JSON | — |
| action | enum | `suppress_alert_only / block_execution` |
| last_reviewed_at | timestamp | nullable |
| renewal_of_rule_id | FK noise_suppression_rules | nullable；续期时新建一行并指向被续期规则，旧行原样保留（batch-276 M-15） |

**硬规则**（batch-276 M-15）：不允许永久 quarantine；单次授权窗口 `effective_until - effective_from` **≤ 90 天**，到期强制复核。Owner 可在到期前**显式重新审批续期**：续期**不修改旧行**的 `effective_until`，而是新建一行（`renewal_of_rule_id` 指向旧行、新的 ≤ 90 天窗口），保留完整审计链。到期未续期的规则自动失效（既不再 `suppress_alert_only`，也不再 `block_execution`），并由提醒任务计入 `quarantine_expiry_overdue_count`（§11.10）。

### 4.21 `project_adapters`

| 字段 | 类型 | 说明 |
|-----|------|------|
| id | UUID | PK |
| project_id | FK | 唯一 |
| adapter_key | varchar(100) | 如 `cameltv-sports` |
| adapter_yaml_ref | varchar(500) | 指向 `docs/standards/project-adapters/*.adapter.yaml` |
| capabilities_yaml_ref | varchar(500) | — |
| prompt_profile_yaml_ref | varchar(500) | — |
| platforms_json | JSON | 启用的端清单 |
| schema_version | varchar(20) | — |
| checksum | varchar(128) | — |
| created_at / updated_at | timestamp | — |

### 4.22 `node_capability_manifests`

| 字段 | 类型 | 说明 |
|-----|------|------|
| id | UUID | PK |
| node_id | varchar(128) | — |
| driver_key | varchar(80) | — |
| driver_version | varchar(40) | — |
| capabilities_json | JSON | `["browser.chromium","browser.trace",...]` |
| platforms_json | JSON | `["linux","windows"]` |
| max_parallel_sessions | integer | — |
| artifact_types_json | JSON | — |
| last_evidence_ref | varchar(255) | 最近一次成功 run 的证据 ID |
| last_heartbeat_at | timestamp | — |
| available | boolean | **必须有 last_evidence_ref 支撑** |


---

## §5 执行状态机

### 5.1 TestRun

```text
DRAFT ─► VALIDATING ─► QUEUED ─► RUNNING
                                   │
                                   ├─► WAITING_HUMAN ─► RUNNING
                                   ├─► TRIAGING ─► RUNNING / COMPLETED
                                   └─► COMPLETED (必须写 outcome)
                                        outcome ∈ {PASS, FAIL, INCOMPLETE, UNKNOWN}

任意状态 ─► BLOCKED / CANCELED / ERROR
```

**规则**：

- `status=COMPLETED` **必须**有 `outcome`；`BLOCKED / CANCELED / ERROR` **必须**没有 `outcome`。
- `BLOCKED` ≠ PASS；`CANCELED` ≠ PASS。
- `TRIAGING` 是分析阶段，不代表最终结果。
- 取消必须给 Runner 发取消信号，并确认进程/浏览器/设备锁已释放。
- 合法转换由 `app/aiqe/services/run_state.py::transition()` 单入口控制，非法转换抛 `InvalidStateTransition`（TA-005 单测必过）。

### 5.2 NodeRun

```text
PENDING ─► READY ─► QUEUED ─► RUNNING ─► PASSED / FAILED / BLOCKED / ERROR
                      │           │
                      │           └─► WAITING ─► RUNNING
                      └─► CANCELED

PENDING ─► SKIPPED (上游失败且策略要求跳过)
```

### 5.3 StepAttempt

```text
QUEUED ─► RUNNING ─► PASSED / FAILED / TIMED_OUT / ERROR
                       │
                       └─► CANCELED
```

**规则**：Attempt 永不被覆盖。重跑追加新 Attempt，`attempt_no` 单调递增。NodeRun 的最终状态由节点策略决定，但**首次失败在 UI 时间线必须可见**。

### 5.4 Defect

见 §4.17 状态流。

### 5.5 RegressionRequest

```text
pending ─► validating ─► running ─► completed
                           │
                           └─► failed
```


---

## §6 Workflow DAG + 调度器

### 6.1 Workflow Graph JSON Schema

```json
{
  "schema_version": "1.0",
  "scenario_key": "SPORT-LIVE-PUBLISH-001",
  "contract_version": "v3",
  "nodes": [
    {
      "key": "create_match",
      "type": "action",
      "driver": "http",
      "operation": "request",
      "capability": "api.http.request",
      "depends_on": [],
      "resource_keys": ["fixture:match"],
      "input": {
        "method": "POST",
        "request_ref": "api_operation:admin.create_match",
        "body_ref": "fixture:match.valid"
      },
      "outputs": { "match_id": "$.data.id" },
      "assertions": [
        {"key": "http_ok", "type": "http_status", "operator": "eq", "expected": 200},
        {"key": "business_ok", "type": "jsonpath", "path": "$.code", "operator": "eq", "expected": 0}
      ],
      "timeout_ms": 15000,
      "retry_policy": { "max_attempts": 1, "retry_on": [] },
      "idempotency_key_expr": "${inputs.body_ref}"
    },
    {
      "key": "admin_configure_live",
      "type": "action",
      "driver": "playwright",
      "depends_on": ["create_match"],
      "resource_keys": ["account:admin_1"],
      "input": {
        "project_binding": "admin_web",
        "script_ref": "ui_script:configure_live_stream",
        "variables": { "match_id": "${nodes.create_match.outputs.match_id}" }
      },
      "assertions": [
        {"key": "publish_confirmation", "type": "ui_state", "operator": "eq", "expected": "success"}
      ],
      "timeout_ms": 60000,
      "retry_policy": { "max_attempts": 1, "retry_on": [] }
    },
    {
      "key": "verify_public_api",
      "type": "action",
      "driver": "http",
      "depends_on": ["admin_configure_live"],
      "input": {
        "method": "GET",
        "request_ref": "api_operation:public.get_match",
        "path_params": { "match_id": "${nodes.create_match.outputs.match_id}" }
      },
      "assertions": [
        {"key": "public_status", "type": "jsonpath", "path": "$.data.status", "operator": "eventually_eq",
         "expected": "live", "deadline_ms": 10000, "poll_interval_ms": 500}
      ],
      "timeout_ms": 15000,
      "retry_policy": { "max_attempts": 3, "backoff_ms": 1000, "retry_on": ["HTTP_502","HTTP_503","CONNECTION_RESET"] }
    },
    {
      "key": "cleanup_test_data",
      "type": "cleanup",
      "driver": "http",
      "depends_on_terminal": true,
      "input": {
        "method": "DELETE",
        "request_ref": "api_operation:admin.delete_match",
        "path_params": { "match_id": "${nodes.create_match.outputs.match_id}" }
      }
    }
  ],
  "edges": [
    {"from": "create_match", "to": "admin_configure_live", "condition": "success"},
    {"from": "admin_configure_live", "to": "verify_public_api", "condition": "success"}
  ],
  "run_policy": {
    "max_parallel_nodes": 3,
    "fail_fast": false,
    "cleanup_node": "cleanup_test_data"
  }
}
```

### 6.2 校验规则（Workflow Validator）

1. 所有 node key 唯一；所有 `depends_on` 存在；无环。
2. 所有变量引用 `${nodes.X.outputs.Y}` 中 X 是 node_key 的传递祖先。
3. `driver` + `capability` 已在 `driver_registry` 注册。
4. 非幂等写操作 **禁止**自动 retry；否则必须声明 `idempotency_key_expr` 或 compensation node。
5. 每条 assertion **必须有** expected / expected_ref；探索模式除外，但必须显式 `type=exploratory`。
6. 涉及 DB/网络/设备写动作必须有 profile policy + 权限校验。
7. 已批准的 Workflow checksum 固定；修改必须新版本。

### 6.3 DAG 调度逻辑（伪码）

```python
async def schedule_ready_nodes(run_id: UUID) -> None:
    async with db.transaction():
        run = await runs.lock_for_update(run_id)
        if run.status not in {RunStatus.QUEUED, RunStatus.RUNNING}:
            return
        workflow = await workflows.get_frozen(run.workflow_definition_id)
        node_runs = await nodes.list_for_update(run_id)

        for node in node_runs:
            if node.status != NodeStatus.PENDING:
                continue
            deps = workflow.dependencies_for(node.node_key)
            if any(dep_failed_without_continue(d, node_runs) for d in deps):
                node.status = NodeStatus.BLOCKED
                node.error_class = "DEP_FAILED"
                continue
            if not all(dep_satisfied(d, node_runs) for d in deps):
                continue
            if not await locks.resources_available(node.resource_keys):
                continue
            if not registry.has_capability(node.driver_key, node.required_capability):
                node.status = NodeStatus.BLOCKED
                node.error_class = "DRIVER_CAPABILITY_MISSING"
                continue
            node.status = NodeStatus.READY
    await dispatch_ready_jobs(run_id)
```

### 6.4 资源锁

- 锁粒度：`project / environment / fixture:<id> / account:<id> / device:<id> / resource:<business-key>`。
- 锁必须有 **TTL + heartbeat + fencing token**，避免 Worker 崩溃后锁死或旧 Worker 恢复后继续写。
- 锁实现**不能**简单标一句"复用 `task_queue.py`"（batch-276 D-7 预检，2026-11-09）：
  - **现状**：`app/core/task_queue.py` 提供 `atomic_claim`（条件 UPDATE + rowcount 校验）与 `reap_stale`（按 `locked_at` / `heartbeat_at` 列回收），**没有 Postgres advisory lock，也没有独立 heartbeat 表**；
  - **要求**：TA-001 代码审计必须复核上述结论并给出文件行号；确认无 advisory lock + 独立 heartbeat 记录后，**TA-010.3 必须自实现** `aiqe/services/resource_lock.py`——Postgres 走 `pg_try_advisory_xact_lock(hashtextextended(lock_key, 0))`，SQLite（dev/test）走条件 UPDATE / 事务串行 + TTL 列，两者统一暴露 `acquire / renew / release` 与 fencing token；
  - **边界**：现有队列认领锁是"任务所有权"，资源锁是"跨 Run 的业务资源互斥"，**不得直接复用**。

### 6.5 Cleanup 协调

- `cleanup` 节点通过 `depends_on_terminal: true` 声明，主流程不论成败都会执行。
- Cleanup 必须幂等；即使重复执行不破坏其他 Run 数据。
- Cleanup 失败只影响其自身状态，不改变主 Run outcome。


---

## §7 Driver 协议与注册表

### 7.1 统一 Driver Protocol

```python
# app/aiqe/drivers/base.py
from typing import Protocol, Any
from pydantic import BaseModel, Field

class DriverCapabilities(BaseModel):
    driver_key: str
    driver_version: str
    capabilities: list[str]
    platforms: list[str]
    max_parallel_sessions: int
    requires_secrets: list[str]
    artifact_types: list[str]

class ValidationResult(BaseModel):
    valid: bool
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

class StepOutput(BaseModel):
    values: dict[str, Any] = Field(default_factory=dict)
    summary: dict[str, Any] = Field(default_factory=dict)
    external_ref: str | None = None

class Driver(Protocol):
    key: str
    async def capabilities(self) -> DriverCapabilities: ...
    async def validate(self, ctx: "RunContext", step: "StepSpec") -> ValidationResult: ...
    async def prepare(self, ctx: "RunContext", step: "StepSpec") -> Any: ...
    async def execute(self, ctx: "RunContext", step: "StepSpec") -> StepOutput: ...
    async def collect(self, ctx: "RunContext", step: "StepSpec", output: StepOutput) -> list["ArtifactInput"]: ...
    async def cleanup(self, ctx: "RunContext", step: "StepSpec", resource: Any) -> None: ...
```

### 7.2 Driver 开发约定

- Driver **禁止**直接访问 FastAPI request global；全部通过显式 `ctx` 注入。
- Driver **不自行**更新 TestRun 状态；只返回结果 + 发事件。
- Driver 的输出不能包含未脱敏 secret。
- `execute()` 必须有外层 timeout + cancellation。
- `cleanup()` 必须幂等。
- 外部工具用 `subprocess` 时必须：timeout + stdout/stderr 限制 + 退出码检查 + 进程组 kill + 临时目录清理。
- Driver 版本 + capability 要进入 Run Snapshot。

### 7.3 V1 必须 Driver 清单

| Driver | 实现基座 | 职责 | 优先级 |
|--------|---------|------|-------|
| `http` | httpx + 现有 `openapi_import_service` | API 执行、变量提取、assertion | P0 |
| `playwright` | 现有 `playwright_executor` + Playwright 1.56 Agents | Web UI；探索/生成/愈合草案；trace/dom/a11y/net/console | P0 |
| `db_readonly` | SQLAlchemy / 项目 driver | SQL 只读事务、参数化、行数/超时限制 | P0 |
| `event` | aiokafka / 临时 webhook | Kafka 消费 / HTTP 回调验证 | P1 |
| `mobile_web` | Playwright device emulation | H5 跨 device 矩阵 | P1 |
| `miniapp` | `minium` / `weapp-dev-mcp` MCP | 微信小程序 | P1 |
| `appium` | Appium MCP Server | Android / iOS 原生 | P1.1 |
| `external_e2e` | subprocess + Adapter 契约 | TesterArmy e2e / browser-use 等 | P1 |
| `keploy` | subprocess | 上下游依赖录制回放 | P1 PoC |
| `midscene` | subprocess | 视觉驱动 fallback | P2 |
| `device` | 项目自定 | IoT / 硬件 | V1.2 |

### 7.4 Driver Registry 与节点自描述

- 每个 `cameltv-node` 启动时上报 `node_capability_manifests` 一行。
- `available=true` 必须有 `last_evidence_ref` 指向一次真实成功 Run。
- 调度器匹配：Node 没有对应 capability → 节点不会收到任务（`DRIVER_CAPABILITY_MISSING`）。
- Manifest 举例：

```yaml
# scripts/node/capabilities.yaml
node_id: node-sports-win-01
available:
  - driver_key: playwright
    driver_version: "1.56.0"
    capabilities: [browser.chromium, browser.trace, browser.video, browser.dom_snapshot, browser.network_events]
    platforms: [windows]
    max_parallel_sessions: 2
    requires_secrets: [TARGET_ADMIN_URL]
    artifact_types: [screenshot, video, trace, har, console_log]
    last_evidence_ref: exec_7731
    last_pass_at: "2026-11-09T14:12:03+08:00"
  - driver_key: http
    driver_version: "0.27.0"
    ...
```

### 7.5 Adapter Contract Test（§9.11 所有 Driver 必过的公共测试）

```text
A. capabilities() 输出满足 schema
B. 未满足条件时 validate 返回 blocker
C. execute 超时后进程/资源释放
D. cancel 后能停止操作
E. 事件重复上报幂等
F. 输出值只在 Run scope 可见
G. 敏感字段进入 event 前被脱敏
H. artifact checksum 正确
I. cleanup 可重复调用
J. Runner 掉线后状态最终变 ERROR/BLOCKED，不是永远 RUNNING
```


---

## §8 Run Event 协议与 SSE 订阅

### 8.1 Event 载体

```json
{
  "schema_version": "1.0",
  "event_id": "uuid",
  "run_id": "uuid",
  "seq": 108,
  "node_key": "open_match_page",
  "step_key": "click_live_entry",
  "attempt_no": 1,
  "event_type": "UI_ACTION_COMPLETED",
  "occurred_at": "2026-11-09T01:12:03.123Z",
  "producer": "playwright",
  "correlation_id": "trace-id",
  "payload": {
    "action": "click",
    "target": { "role": "button", "name": "进入直播间" },
    "duration_ms": 143,
    "page_url": "https://test.example/live/123",
    "result": "completed"
  }
}
```

### 8.2 最低事件类型

```text
RUN_CREATED / RUN_VALIDATING / RUN_QUEUED / RUN_STARTED / RUN_FINISHED
NODE_READY / NODE_QUEUED / NODE_STARTED / NODE_FINISHED / NODE_BLOCKED
STEP_STARTED / STEP_LOG / STEP_FINISHED
API_REQUEST / API_RESPONSE                               (body 采样 + 脱敏)
UI_NAVIGATION / UI_SNAPSHOT / UI_ACTION_STARTED / UI_ACTION_COMPLETED
CONSOLE_ERROR / NETWORK_REQUEST / NETWORK_FAILED / NETWORK_RESPONSE
ASSERTION_EVALUATED
ARTIFACT_CREATED
LIVE_FRAME                                               (节点每 2s 推一张缩略图)
INTERFERENCE_SIGNAL_DETECTED
TRIAGE_STARTED / TRIAGE_HYPOTHESIS / TRIAGE_FINISHED
CLEANUP_STARTED / CLEANUP_FINISHED
```

### 8.3 Outbox 事务模式

**关键**：业务更新与事件必须在**同一 DB 事务**内写 `run_events + event_outbox`，不能"先推 WebSocket 再存 DB"。

```python
# app/aiqe/services/event_service.py
async def append_event(ev: EventCreate) -> RunEvent:
    async with db.transaction():
        # 1) 幂等
        if await repo.exists_producer_event(ev.run_id, ev.producer_event_id):
            return await repo.get_by_producer_event(ev.run_id, ev.producer_event_id)
        # 2) 分配 seq（方言相关，见 §8.3.1 与附录 C）
        seq = await repo.next_seq(ev.run_id)
        # 3) 写 run_events
        row = await repo.insert_event(ev, seq=seq)
        # 4) 写 event_outbox
        await repo.insert_outbox(row.id)
        # 5) 同事务内投影状态（NodeRun/StepAttempt）
        await _project_state(row)
    # 6) 事务外触发 dispatcher
    await dispatcher.notify(row.run_id)
    return row
```

#### 8.3.1 `seq` 分配：SQLite vs PostgreSQL（batch-276 D-1）

**单 Run 严格递增**是协议硬约束，两种方言必须用不同机制，但对外语义一致（唯一索引 `(run_id, seq)` 兜底，冲突即回滚重试 ≤ 3 次）：

| 方言 | 机制 | 说明 |
|------|------|------|
| SQLite（dev/test） | `run_seq_counters(run_id PK, last_seq bigint)` 计数器行 `INSERT ... ON CONFLICT(run_id) DO UPDATE SET last_seq = last_seq + 1 RETURNING last_seq` | SQLite 单写者语义天然串行；`(run_id, seq)` 唯一索引兜底；不依赖 advisory lock |
| PostgreSQL（prod） | 事务内先 `pg_advisory_xact_lock(hashtextextended(run_id::text, 0))`，再对计数器行 `UPDATE ... RETURNING last_seq`（首事件 `INSERT ... ON CONFLICT DO NOTHING`） | 事务提交自动释放咨询锁；不用裸 `MAX(seq)+1`，避免并发撞号 |

**禁止**：应用层 `max(seq) + 1` 后直接插入（无锁时并发必撞）；把 `event_outbox.id`（全局自增）当作 Run 内 seq。
**TA-006 验收追加**：SQLite 与 PostgreSQL 各跑 1000 条并发事件，seq 连续、无重复、无跳号。

### 8.4 SSE 订阅

```text
GET /api/v1/runs/:id/events?after_seq=N
    Accept: text/event-stream
    Last-Event-ID: 42      (可选)

response:
    id: 43
    event: STEP_STARTED
    data: { ... }

    id: 44
    event: UI_ACTION_COMPLETED
    data: { ... }
```

**规则**：

- 初次订阅支持 `Last-Event-ID` 或 `after_seq`。
- 浏览器刷新后拉 `GET /events?after_seq=N` 补事件。
- UI 不依赖单次事件成功：状态以 `GET /runs/:id` 为准，event 是时间线。
- 每 Run `seq` 严格单调递增；重复事件按 `event_id` 去重。
- 事件超过一定量分页；前端只保留当前窗口。

### 8.5 前端 `useRunEvents()` 约定

```ts
function useRunEvents(runId: string) {
  // 1) GET /runs/:id 取 latest_seq
  // 2) GET /events?after_seq=localSeq 取历史
  // 3) new EventSource('/events?after_seq=latest_seq')
  // 4) 按 seq 更新本地 timeline
  // 5) 断线指数退避重连（3/6/12/30s）
  // 6) 超过 N 次重连 → 切轮询并在 UI 显示"实时连接中断"
  // 7) 用户刷新 → 从 API 重新取状态，不依赖 browser storage
}
```


---

## §9 Assertion 引擎（含 24 准则接线）

### 9.1 Assertion DSL

统一使用白名单操作符，**禁用** `eval() / exec()`。

**值操作符**：`eq / neq / in / not_in / gt / gte / lt / lte`。
**结构操作符**：`exists / not_exists / not_empty / contains / regex / json_schema_valid`。
**时间操作符**：`eventually_eq`（带 `deadline_ms` + `poll_interval_ms`）。
**视觉操作符**：`visual_diff_below`（阈值来自 Profile/基线）。
**HTTP 操作符**：`http_status / response_time_below`。
**DB 操作符**：`db_row_exists / db_value_eq`（只允许登记 SQL Template）。
**状态操作符**：`state_transition`（基于 state machine 校验）。
**媒体操作符**：`media_ready / first_frame_below / playback_error_absent`（后续专项插件提供）。
**交互准则**：`interaction_rule_satisfied`（绑 A01-A24 的断言库，见 §9.3）。

### 9.2 Eventually assertion

```python
# 统一轮询器
async def poll_until(
    actual_fn,
    operator,
    expected,
    deadline_ms: int,
    poll_interval_ms: int,
) -> AssertionResult:
    deadline = now() + deadline_ms
    snapshots = []
    while now() < deadline:
        actual = await actual_fn()
        snapshots.append((now(), actual))
        if operator(actual, expected):
            return AssertionResult(status="PASS", actual_json=actual, snapshots=snapshots)
        await sleep(poll_interval_ms)
    return AssertionResult(status="FAIL", actual_json=snapshots[-1][1], snapshots=snapshots)
```

**规则**：失败也要保留最后一次实际值 + 完整耗时。不允许无限轮询。

### 9.3 24 准则接入（复用已有 asset-map 标准）

复用 `docs/standards/test-asset-map-standard.md` 定义的 24 条交互准则 R01-R24 + 可执行断言 A01-A24：

| 准则 | 断言 ID | 落点 |
|------|--------|------|
| R01 可发现性 | A01 | Playwright `locator.isVisible()` + role name 校验 |
| R07 文本容器溢出 | A07 | DOM 测量 `scrollWidth > clientWidth` |
| R11 权限可见性 | A11 | 按角色加载后 `locator.count() == 0` |
| R12 数据权限(IDOR) | A12 | 跨 ID 请求必 403（**V1 补 fixture**） |
| R21 对比度 | A21 | axe-core / WCAG ≥4.5:1 |
| R22 响应式三档 | A22 | viewport 1280/1440/1920 + 375/414，DOM 校验 |
| R23 键盘焦点 | A23 | `Tab` 序列遍历 |
| ... 共 24 条 ... | | 参见 `.claude/skills/interaction-case-augmenter/references/interaction-rules.json` |

**接线方式**：

- 节点侧用 `scripts/test-asset-map/run_assertions.py` 执行 `web / http` 子集。
- 结果写入 `assertion_results.rule_id = "A21"`。
- 前端 `<StepTimeline />` 按 `rule_id` 着色显示。

### 9.4 Oracle 层标记

每条 assertion 必须显式声明 Oracle 来源：

```json
{
  "assertion_key": "fav_persisted_backend",
  "oracle_layer": "REQ | STD | PATTERN",
  "oracle_ref": "contract:REQ-FAV-001#AC-001#observable_checks[1]",
  "type": "jsonpath",
  "operator": "eq",
  ...
}
```

CI 守卫（TA-020.3）：任何 case 中有 assertion 缺 `oracle_layer` 一律拒 PR。
"页面正常/操作成功" 禁止作为预期（延续 interaction-methodology §3）。

### 9.5 AI 介入的边界

- AI 只能**补充** `explanation` 字段；
- AI **不能**覆盖 `deterministic assertion` 的 `status`；
- `evaluated_by=ai_assisted` 的 assertion **必须**同步保留 `evaluated_by=deterministic` 的原始结果；
- AI 的视觉断言只作为建议，`visual_diff_below` 的通过与否由阈值计算，不由 AI 判断。


---

## §10 Agent 服务与 Skill 开放标准

### 10.1 统一 Agent Contract

```python
# app/aiqe/agents/base.py
from pydantic import BaseModel
from typing import Literal

class AgentRequest(BaseModel):
    task_id: UUID
    project_id: UUID
    actor_id: UUID
    agent_key: str                    # A0..A6
    agent_version: str                # {prompt_v}-{schema_v}-{tools_v}-{model_v}
    input_schema_version: str
    context_refs: list[str]           # 用 artifact ref / 文件 URI，不塞大文件
    payload: dict
    allowed_tool_keys: list[str]
    deadline_seconds: int = 120
    token_budget: int | None = None

class AgentResult(BaseModel):
    task_id: UUID
    agent_key: str
    agent_version: str
    status: Literal["SUCCEEDED", "NEEDS_HUMAN", "FAILED", "CANCELED"]
    output_schema_version: str
    output: dict | None
    evidence_refs: list[str]
    tool_calls: list[dict]
    warnings: list[str]
    error: dict | None
    usage: dict | None
```

每次调用必须写一行 `agent_executions`（P0-1 校准规则）。

### 10.2 V1 Agent 清单与工期

| Agent | V1 必须 | 职责 | 输入 | 输出 | 人日 |
|------|-------|------|------|------|-----:|
| **A0 Orchestrator** | 必须 | 路由任务、读上下文、创建 AgentExecution、人工确认点 | 用户请求 + 项目上下文 | AgentTaskPlan | 5-7 |
| **A1 Requirement Assurance** | 必须 | PRD→AC + 歧义列表 + 来源映射 | PRD/原型/代码 diff/会议纪要 | RequirementContract 草案 | 6-8 |
| **A2 Test Design & Review** | 必须 | 场景/用例草案 + 覆盖矩阵 + BugPattern 命中 | 冻结契约 + 历史 BugPattern + API schema | TestScenario/TestCase 草案 | 8-12 |
| **A3 Workflow Planner** | 必须 | 生成 DAG 草案（必过 Validator） | 已批准 TestCase + Driver Registry + Profile | WorkflowDefinition 草案 | 5-7 |
| **A4 Failure & Interference Triage** | 必须 | 多假设根因 + 反事实实验计划 + Defect Draft | Run events / artifacts / snapshot / 并发 run | TriageCase + Hypotheses + Defect Draft | 10-14 |
| **A5 Change Impact & Regression** | 必须 | 影响图 + 候选回归集 + 强制回归集 | PR diff / commit / 依赖图 / Bug links | ImpactGraph + RegressionPlan | 6-8 |
| **A6 Learning Curator** | V1 后半/1.1 | 已确认缺陷→BugPattern 候选 + 评估 | 已确认 Defect / 生产事故 / 人工标注 | LearningCandidate | 6-9 |
| UI Explorer Adapter | 必须能力 | 复用 Playwright MCP / e2e | 测试意图 + 受限 URL | 操作事件 + DOM/A11y + 脚本草案 | 3-6 |
| Env/Data Planner | 必须基础 | 规则优先，非 LLM | Workflow + Profile + fixture | Readiness Report | 4-6 |

**合计约 46-65 人日**（原版 92-125 人日偏向重复建设；合并复用已有能力）。

### 10.3 三阶段计划生成管线

A2 不是一把梭，而是三阶段：

```text
A2.1 场景族生成 ──► ScenarioFamily JSON
  ↓
A2.2 断言绑定  ──► 24 准则 + 项目 Oracle + BugPattern 摘要 注入 prompt
  ↓
A2.3 覆盖率自检──► 断言覆盖率 / 接口分配率 / 链路可执行性 三指标 + GAP 清单
```

**每阶段单独一次 LLM 调用**，各自落 `agent_executions`。大文档超时走异步 task_queue（修 SPORT-INT B1）。

### 10.4 Skill 开放标准（可移植性）

所有自己写的 Agent 能力统一封装为 **Agent Skills 开放标准**（Anthropic 2025-12-18 发布，Codex CLI / Cursor / Copilot 均适配）：

```text
.claude/skills/<skill-name>/
  SKILL.md              # YAML frontmatter + 自然语言指令（progressive disclosure）
  references/           # 可选参考资料
  scripts/              # 可选可执行脚本
```

SKILL.md 示例：

```markdown
---
name: noise-hint-agent
description: 疑似测试噪音归因。输入失败证据 + 当前环境 active feature flag + 并发 run，输出 1-3 个疑似混杂因素 + 证据引用。不替代人判断。
---

## When
失败归因阶段，A4 规则检测后、人复核前调用。

## Inputs
- execution_events: SSE stream dump
- active_flags: list[FeatureFlag]
- concurrent_runs: list[RunSummary]

## Output schema
{ "hints": [{ "factor": "...", "evidence_refs": [...], "classification": "..." }] }

## Rules
- 必须给证据引用（事件 ID / flag ID / 并发 run ID）
- 不输出置信度百分比（无标注历史）
- 严禁推断 "是 bug" / "不是 bug"
- 多因素共存时输出多条 hint
```

### 10.5 平台内 Skill 注入管线

```python
# app/services/ai_service.py（已有基础上）
def _load_skill_context_for(task_type: str, project_adapter: ProjectAdapter) -> str:
    base = [
        "tests/test-case-standards/interaction-testing/interaction-methodology.md",
        "tests/test-case-standards/interaction-testing/admin-and-consumer-interaction.md",
        "tests/test-case-standards/interaction-testing/platform-profiles.md",
        ".claude/skills/interaction-case-augmenter/references/interaction-checklist.md",
    ]
    profile = project_adapter.load_profile()      # 项目 L2 适配器
    extra = [p.references for p in profile.applicable_profiles(task_type)]
    extra.append(load_project_bug_pattern_digest(project_adapter.key, limit_bytes=8*1024))
    return concat_with_total_cap(base + extra, cap_bytes=24*1024)
```

**同步修复**：把 `interaction-case-augmenter/SKILL.md §3` 里硬编码的 xinyuwadao/RuoYi 等项目词移到 `docs/standards/project-adapters/*.prompt-profile.yaml`。

### 10.6 Prompt 模板通用规范

每个 Prompt 至少包含：
1. 角色目标；
2. 允许使用的事实来源；
3. 禁止假设/禁止行为；
4. 输出 JSON Schema；
5. 引用证据规则（必须 evidence_refs）；
6. 冲突/不确定处理方式；
7. 工具使用边界；
8. 安全脱敏规则；
9. 输出版本号。

网页、Issue、PR 中的 Prompt Injection **不允许**改变工具白名单。

### 10.7 Agent 版本发布

Agent 版本由 `agent_key + prompt_version + schema_version + tools_version + model_config_version` 唯一确定：
- 改 Prompt 必须跑 eval（§21）；
- 改工具 Schema 必须跑 contract tests；
- 改模型必须跑固定 benchmark；
- 旧 `agent_executions` 永远保留原版本。


---

## §11 噪音与干扰因果治理

### 11.1 定义

**Noise = 测试过程中存在影响观测或执行的非目标因素**。但干扰因素本身也可能暴露真实缺陷（例如其他功能的浮层挡住主流程按钮——这是**产品集成缺陷**，不是"无关噪音"）。

因此系统**必须分离**：

- **Execution Outcome**：`PASS / FAIL / INCOMPLETE / UNKNOWN`
- **Failure Attribution**：`PRODUCT_DEFECT / CROSS_FEATURE_DEFECT / ENVIRONMENT / TEST_DATA / CONCURRENCY / THIRD_PARTY / NETWORK / TIME / AUTOMATION / REQUIREMENT_GAP / FLAKY / UNKNOWN`
- **Interference Observation**：是否观察到某个异常信号
- **Release Impact**：是否影响需求验收 / 发布门禁

**`NOISE_SUSPECTED / BLOCKED / SKIPPED` 永远不计 PASS**（ADR-AIQE-005）。

### 11.2 干扰分类目录

| 分类 | 典型信号 | 必采证据 | 隔离/验证动作 |
|------|---------|---------|--------------|
| ENVIRONMENT | 5xx、服务重启、健康检查失败、部署中 | 服务健康快照 / 部署时间线 / 日志 / Trace | 固定 Build；等待健康；同环境隔离复跑 |
| TEST_DATA | 同一记录被其他 Run 修改、fixture 不唯一 | namespace / row version / audit log | 每 Run 唯一 namespace；重新造数；快照对比 |
| CONCURRENCY | 同账号/token/订单被并行测试操作 | lock key / owner / 操作时间线 | 锁资源；串行复跑；账号池隔离 |
| THIRD_PARTY | API timeout / rate limit / 供应商数据变动 | 请求响应 / 依赖健康 / external correlation ID | Mock / Sandbox / record-replay；单独真实联调 |
| NETWORK | DNS 失败、RST、丢包、TLS 错误 | 网络指标 / DNS / TLS / HAR | 固定网络 Profile；替换节点 |
| TIME | 时区、赛事状态、定时任务、缓存过期 | UTC / clock offset / scheduler logs | 可控时钟；固定赛事时间；eventually assertion |
| CROSS_FEATURE | 公共 Header、广告、弹窗、支付 SDK、权限组件 | 代码变更 / 页面层级 / 请求 / DOM 事件 | Feature Profile 对照；专项集成测试 |
| UI_OVERLAY | overlay、焦点抢占、滚动、动画、异步渲染 | DOM / A11y / 截图 / hit target / 时间线 | 禁用动画；等业务状态；复核真实点击区域。分类元数据 **`requires_ui_surface: true`**（batch-276 M-13） |
| AUTOMATION | locator 失效、浏览器崩溃、脚本异常、资源耗尽 | Stack / Trace / Runner log / 浏览器版本 | 重建 Worker；脚本自检；先证实产品状态 |
| REQUIREMENT_AMBIGUITY | PRD / 原型 / 接口描述冲突 | 需求版本 / 变更记录 / 评审记录 | 标记 NEEDS_PRODUCT_DECISION，不猜测预期 |
| UNKNOWN | — | — | 转人工 |

**分类元数据与 adapter capability 启停**（batch-276 M-13）：

- 干扰目录中 `UI_OVERLAY` 带 `requires_ui_surface: true`，含义：该类**检测与复跑**必须有真实 UI 表面（浏览器 / 移动端 / 小程序），纯 API / DB / 事件 Driver 不得声称支持；
- Driver 必须在 §7.1 `DriverCapabilities.capabilities` 声明 **`ui.overlay.observe`**（能检测浮层干扰）与 **`ui.overlay.control`**（能禁用动画 / 关闭浮层）。两条独立声明，不合并成一个 capability；
- 调度器分配"UI_OVERLAY 检测 / 复跑"节点前校验目标 Driver capability：
  - 缺 `ui.overlay.observe` → **不派发**，事件记 `unsupported`（不造假字段、不降级为 PASS）；
  - 只有 observe 无 control → 允许"观察 + 人工复核"路径，不执行"禁用动画"动作；
- capability 声明必须对应 §4.22 `node_capability_manifests.last_evidence_ref` 的真实 run 证据，**不接受手写声明**。

### 11.3 Run 开始前的预防（比失败后猜测更重要）

#### A. Execution Profile（必配三档）

- `core_isolated`：隔离当前目标，极小化非目标因素；
- `integration`：保留跨需求真实交互；
- `external_live`：连真实上游，验证外部集成。

Profile checksum 必须落库；不同 Profile 的结果**不能当作同一条件下重复**。

#### B. 数据隔离

- Run 级 namespace：`project_id/run_id/fixture_key`；
- 默认每条 Run 独立用户/订单/赛事/设备绑定；
- 共享账号必须有资源锁；
- 造数返回的业务 ID 写 RunContext，不写死到用例；
- cleanup 只删 Run 自己的数据；
- 无法隔离 → 节点串行，不允许伪并行。

#### C. 依赖确定性

- fixture 固定响应版本 + hash；
- Mock/Sandbox/Live 模式写入 Run 快照；
- 外部服务不可用时，不让无关用例误报成产品缺陷；
- 真实集成失败仍单独报告，不能被 mock PASS 抵消。

#### D. 时间与随机

- Run 固定 timezone / locale / clock reference；
- 赛事过期、订单结束用注入 clock；
- 随机数据记录 seed；
- 定时任务版本 + 运行窗口入 snapshot。

#### E. 变更与配置快照

Run 启动时固定：application build/commit / API schema version / feature flags / 第三方模式 / 浏览器版本 / viewport / 网络 Profile / 账号角色 / 数据 namespace / 环境依赖健康状态。

### 11.4 反事实对照重放矩阵（E1-E6）

**原则**：每次对照只改变一个被怀疑因素，固定其他条件。

| 实验 | 固定项 | 唯一变化项 | 能回答的问题 |
|------|-------|-----------|------------|
| **E1 同 Build 重跑** | Build / Profile / 数据 / 浏览器 | 执行时间 | 是否偶发 / 不稳定 |
| **E2 数据隔离重跑** | Build / 环境 / 浏览器 / 上游模式 | 独立 fixture namespace | 是否数据污染 / 共享数据竞争 |
| **E3 外部依赖回放** | Build / 数据 / 浏览器 | Live → Recorded Fixture | 失败是否由外部响应差异触发 |
| **E4 跨功能 Profile 对照** | Build / 数据 / 设备 | feature integration on/off 或 fixture | 是否受另一业务功能影响 |
| **E5 Worker 对照** | Build / 数据 / Profile | 更换执行 Worker / 浏览器实例 | 是否 Runner / 节点环境问题 |
| **E6 网络 Profile 对照** | Build / 数据 / 服务版本 | 正常 vs 受控弱网 / 代理 | 是否网络层问题 |

**硬规则**：

- 复跑前先判断写操作幂等，避免重复扣款、重复发通知；
- **对照实验不得对生产执行**；
- 一个因素变化后结果变 → 只能说该因素是**候选因果**；仍需检查产品设计是否应该承受该因素；
- 多因素共同作用时**保留多个假设**，不强行选单一原因；
- 真实用户路径因跨功能冲突失败 → **作为产品/集成缺陷**，不得被隔离测试 PASS 掩盖；
- 对照实验改动两个变量 → 实验**标记 INVALID**，不可用于根因判断。


### 11.5 失败后归因工作流（A4 Triage）

```text
Deterministic Assertion FAIL / Runner Error
                  │
      采集失败点前 15s - 后 10s 的事件窗
                  │
       规则 Detector + Interference Signals
                  │
          LLM 生成多个根因假设
                  │
       按证据成本/安全选验证实验（E1-E6）
                  │
          Runtime 执行单变量对照
                  │
       更新支持证据 / 反证，检查结果
                  │
    ┌─────────────┼─────────────┬─────────────┐
    ▼             ▼             ▼             ▼
 PRODUCT     CROSS_FEATURE  ENV/DATA/...   UNKNOWN
 DEFECT        DEFECT        BLOCKED        HUMAN
```

### 11.6 失败事件时间窗必采清单

默认采集失败点前 15 秒到后 10 秒：

- 当前 Step / Node；
- API 请求、响应、耗时、correlation ID；
- Browser action / DOM / A11y / 截图 / Network / Console；
- 环境健康 / 节点资源状态；
- 最近相关的部署 / 定时任务 / feature flag 变更；
- 当前数据 namespace / 锁 / 并发 Run；
- 上下游请求 / 外部状态 / 依赖健康。

**不得**为了采集噪音保存未脱敏敏感用户信息。

### 11.7 A4 归因输出 Schema

```json
{
  "triage_case_id": "uuid",
  "execution_outcome": "FAIL",
  "attribution_status": "NEEDS_EXPERIMENT",
  "hypotheses": [
    {
      "classification": "CROSS_FEATURE_DEFECT",
      "scope": "shared_header_and_live_entry",
      "summary": "直播按钮点击区域被浮层覆盖",
      "supporting_evidence": ["artifact:screenshot-1", "event:104", "artifact:dom-1"],
      "contradicting_evidence": [],
      "missing_evidence": ["integration_profile_replay"],
      "proposed_experiment": {
        "profile": "core_isolated",
        "change_only": "overlay_feature_fixture",
        "expected_observation": "click target is reachable"
      },
      "confidence": null,
      "status": "PROPOSED"
    },
    {
      "classification": "AUTOMATION_DEFECT",
      "summary": "locator 可能绑定到隐藏的同名元素",
      "supporting_evidence": ["artifact:playwright-trace"],
      "contradicting_evidence": [],
      "missing_evidence": ["visible_element_count"],
      "proposed_experiment": {"change_only": "locator_strategy"},
      "confidence": null,
      "status": "PROPOSED"
    }
  ],
  "human_review_required": true
}
```

**规则**：`confidence` 初期保持 null；由规则/验证结果产生证据等级，不让模型自由填百分比装置信度。

### 11.8 自动分类 / 自动建缺陷阈值

初期安全规则：

- 仅"环境健康检查明确 FAIL 且无业务 assertion" → 可自动分类 `ENVIRONMENT_BLOCKED`；
- 仅"browser process crashed 且业务页面未执行到" → 可分类 `AUTOMATION_ERROR`；
- 任何真实业务 assertion FAIL，**即使同时发现干扰**，必须保留 FAIL；
- `CROSS_FEATURE_DEFECT` 必须有实际用户路径失败的证据；
- AI **仅创建 Defect Draft**，不得未经确认自动关闭或归为非缺陷；
- 证据不足 → `UNKNOWN`，不允许编造根因。

成熟后依据标注数据设阈值，**precision 优先**，不以自动分类率作 KPI。

### 11.9 已知干扰规则（Noise Suppression）

每条规则必须包含（§4.20 已定表结构）：
- scope / 分类 / 匹配条件 / 生效起止 / Owner / 原因 / 关联已确认问题 / 证据链接 / action (`suppress_alert_only` 或 `block_execution`) / 到期提醒。

**严禁**：
- 全局忽略某域名/错误类型而不记账；
- 把"已知问题"直接改为 PASS；
- 永久 quarantine（单次授权 `effective_until - effective_from ≤ 90 天`；到期前 Owner 必须**显式重新审批续期**，续期新建规则行并经 `renewal_of_rule_id` 指向旧行，旧行不改——见 §4.20，batch-276 M-15）；
- 因为"是其他需求负责"就不报告跨功能影响。

### 11.10 噪音指标（周报）

- `confirmed_product_defect / all_failed_runs`
- `false_positive_ratio = 被确认为非产品缺陷的 Bug Draft / 所有 Bug Draft`
- `unknown_attribution_ratio`
- `environment_blocked_ratio`
- `data_contamination_rate` / `concurrency_rate`
- `flaky_rate`（首跑失败而受控重跑通过）
- `triage_median_time`
- `replay_verification_success_rate`
- `defect_escape_rate`（上线后发现而测试未识别）
- `quarantine_expiry_overdue_count`

指标用于找环境/流程瓶颈，**不用于给测试人员压缺陷数**。


---

## §12 缺陷闭环与一键回归

### 12.1 自动生成 Defect Draft 的硬门槛

- 至少一个 **确定性 Assertion FAIL**，或经审核的探索性发现；
- 有需求 / AC 或人工说明作为**预期基准**；
- 有**实际结果**和至少一个证据引用；
- 已检查环境和 Driver 错误；
- 若归因仍 `UNKNOWN` → 只能创建"待分诊问题"，**不能**直接称为产品 Bug。

### 12.2 开发复现步骤自动结构化

```json
{
  "environment": "sports-test5 / build=16.0.3 / commit=4c3a3705",
  "account_role_ref": "ref:test_user.premium",
  "preconditions": [
    { "ref": "fixture:match.valid", "resolved_id": "match_7721" }
  ],
  "steps": [
    { "seq": 1, "action": "POST /admin/match", "data_ref": "fixture:match.valid" },
    { "seq": 2, "action": "UI: 后台登录 + 配置直播源" },
    { "seq": 3, "action": "GET /public/match/7721" }
  ],
  "expected": "public.status == 'live'",
  "actual": "public.status == 'draft'",
  "evidence_refs": ["artifact:screenshot-3", "artifact:har-1", "event:seq-82"],
  "ruled_out_factors": ["ENVIRONMENT", "AUTOMATION"],
  "pending_factors": ["CACHE_DELAY"]
}
```

### 12.3 一键回归 API

```http
POST /api/v1/defects/:id/regressions
{
  "fixed_commit_sha": "40-hex-sha",
  "selection_mode": "scenario",
  "selected_case_ids": [],
  "options": { "force_p0_smoke": true }
}
```

**后端规则**：

1. 读取 `defect.linked_execution_id → source run`；
2. 用户确认修复 commit / build；
3. A5 Impact Agent 提供候选集合；
4. 规则引擎添加强制风险回归集（登录/权限/支付/租户隔离等）；
5. 创建 `RegressionRequest`（固定 Profile + env_snapshot_id + seed_data_ref）；
6. 创建新 `TestRun`（`retest_of = source_run_id`）；
7. 对比每条 AC + Assertion 的前后结果；
8. **回归 PASS 只生成"建议关闭"，不自动关闭**；
9. 若首跑失败重试成功 → 标 `FLAKY_REVIEW`，**不以最终成功覆盖首次失败**。

**UI 入口**：在 `defect/:id` 顶部按钮，仅 `fixing / pending_review` 状态可用。回归结果页展示 **前后 trace / screenshot / console / API response** 的三路对比视图。

### 12.4 对比视图字段

- 左栏：源 Run；右栏：回归 Run；中栏：diff；
- 对每条 assertion 显示 `expected / actual before / actual after`；
- 对每条 screenshot 支持像素 diff；
- 对每个 request 显示 `headers diff / body diff / status diff`；
- 对 trace 允许并排打开两个 Playwright trace viewer（iframe）。


---

## §13 多端 Driver 与跨端对照

### 13.1 业务意图 vs 端侧动作分离

同一个 AC 可以绑定多个平台，具体动作由 `Platform Adapter` 实现：

```yaml
acceptance_criterion:
  key: AC-ORDER-001
  intent: 用户登录后能查看自己的订单
  given: [user.status == active, user.order_count == 3]
  when: user_opens_order_list
  then:
    - visible_order_count == 3
    - all_orders_belong_to_current_user == true

platform_bindings:
  web:               { driver: playwright,  workflow_ref: ui:web:orders:list }
  mobile_web:        { driver: playwright,  workflow_ref: ui:mweb:orders:list, devices: [iPhone 14, Pixel 7] }
  android:           { driver: appium,      workflow_ref: ui:android:orders:list }
  ios:               { driver: appium,      workflow_ref: ui:ios:orders:list }
  wechat_mini_program:{ driver: miniapp,    workflow_ref: ui:wxmp:orders:list }
```

### 13.2 跨端链路（admin ↔ consumer 配合验证）

新增 **Workflow 模板** `interaction_chain`，由一个主 Workflow 编排多个跨端子任务串行执行：

```yaml
chain_id: EVENT-PUBLISH-TO-CONSUMER
nodes:
  - key: admin_create       # 后台 web
    driver: playwright
    adapter: cameltv-admin
    outputs: { event_id: "$.data.id" }
  - key: data_state         # 数据层校验
    driver: db_readonly
    assertion: "SELECT state FROM events WHERE id=${event_id}  --> 'PUBLISHED'"
  - key: api_list           # 接口层
    driver: http
    assertion: "$.data[?(@.id==${event_id})]"
  - key: consumer_h5        # C 端 H5
    driver: playwright
    adapter: cameltv-h5
  - key: consumer_mp        # 微信小程序
    driver: miniapp
    adapter: cameltv-mp
```

**关键**：任何步骤失败 → chain 立即停 + **记录"失败在哪一跳"**（admin/data/api/h5/miniapp），直接进缺陷归因。

### 13.3 各端 Driver 覆盖要求

| 端 | V1 工具 | 必覆盖 | 不可做 |
|----|--------|--------|--------|
| PC Web | Playwright 1.56 + Agents | viewport / 浏览器矩阵 / DOM / A11y / 表单 / Network / Console / 弱网 | - |
| Mobile Web | Playwright device emulation + 真机 Playwright for Android | 触控 / 软键盘 / 横竖屏 / Nav history | 仅 viewport 仿真代替真实 iOS Safari |
| Android 原生 | Appium | 设备分配 / App install / 版本 / 权限 / deep link / reset / 截图录屏 / crash log / 网络代理 | 模拟器通过写成"真实设备矩阵通过" |
| iOS 原生 | Appium WDA（**先解 C84-1 阻塞**） | 同上 | - |
| 微信小程序 | `minium` / `weapp-dev-mcp`（**不能靠 Playwright**） | 开发工具版本 / 基础库 / 真机预览 / 微信客户端兼容 / 自动化登录限制 | 假设 Playwright 能覆盖小程序 |
| Windows/macOS Desktop | Playwright Electron / Appium Windows / UIA / AppleScript | — | 远程无桌面 session 时假设能做视觉 |
| 硬件 / IoT | 项目自写 Adapter | connection lifecycle / command schema / telemetry schema / state machine / safety interlock / emergency stop / lab inventory / 复位 | 让模型直接向真实硬件发任意命令 |

### 13.4 跨端对照矩阵 UI

```text
                │ PC Chrome │ Android Chrome │ iOS Safari │ 小程序-微信 │
────────────────┼───────────┼────────────────┼────────────┼────────────┤
AC-ORDER-001.1  │  PASS ✓   │  PASS ✓        │  FAIL ✗    │  PASS ✓    │  (iOS 点击目标被浮层挡)
AC-ORDER-001.2  │  PASS ✓   │  PASS ✓        │  PASS ✓    │  PASS ✓    │
AC-ORDER-001.3  │  PASS ✓   │  BLOCKED ⊘     │  PASS ✓    │  NO_DRIVER │  (Android 登录准备失败，不算通过)
```

每行悬停显示 **跨平台语义类型**（延续 `platform-profiles.md §6`）：
- `shared_behavior`：所有端期望一致，必须全 PASS；
- `platform_specific_behavior`：允许端差异（如 iOS 没有返回键手势），每端预期分别写；
- `unsupported_behavior`：本端不支持（标 `SKIP` + 理由）；
- `unknown_behavior`：未定义 → 报 `BLOCK`。

比较前必须检查：需求契约版本、build SHA、profile、fixture seed、用户角色是否一致。不同条件结果**只能并列查看**，不是 A/B 对照。

### 13.5 Domain Pack（领域知识包）

通用内核不写死业务对象。Domain Pack 提供：
- business entity vocabulary（如赛事/球队/直播源/比分）
- fixture templates
- API contract aliases
- domain-specific assertions
- risk heuristics
- historical BugPattern
- scenario templates
- optional specialized drivers

**V1 预定**：
- `sports-pack`：赛事、球队、赛程、直播间、直播源、比分、赛事状态、会员、广告位、媒体质量
- `ecommerce-pack`：商品、库存、购物车、订单、优惠券、支付、物流、退款（future-wayu 可用）
- `saas-pack`：Tenant、Organization、Role、Permission、Subscription、Workflow、Audit Log
- `iot-pack`：Device、Binding、Command、Telemetry、Alert、Firmware、Gateway

Domain Pack 与 Project Adapter 分开：前者是领域能力，后者是当前项目**启用哪些系统和 Driver**。


---

## §14 OSS 组件准入与评估

### 14.1 推荐复用矩阵（不重造）

| 项目 | 适合复用的能力 | 定位 | 许可证 / 风险 |
|------|---------------|------|--------------|
| **Microsoft Playwright MCP** | AI 浏览器探索 / DOM/A11y snapshot / 调试 | 探索模式首选；UI Explorer Agent 经受限 MCP tool 调用 | Apache-2.0；MCP 不是安全边界，需隔离运行 |
| **Playwright Test Agents (Planner/Generator/Healer)** | Web UI 规划/生成/愈合 | `cameltv-node` 内 `npx playwright init-agents`；platform 通过 `kind=web` 调度 | Apache-2.0；Playwright 官方 1.56+ |
| **TesterArmy e2e** | 自然语言 Agent 步骤 + 明确 locator/assertion；Web/iOS/Android engine；缓存/重放 | **2 周 PoC** 后决定主/辅 | Apache-2.0；1.0 前活跃开发，API 可能变更；固定版本 |
| **Appium** | 原生/混合/移动 Web；多 Driver 生态 | V1.1 原生 App 基座 | Apache-2.0；成熟 WebDriver |
| **Keploy** | API 流量录制 / 依赖回放 / DB&MQ 捕获 | **上下游噪音 PoC**；eBPF 权限审计 | Apache-2.0；采集内容必须脱敏 |
| **browser-use** | 复杂浏览流 / 表单 / 多站 | 作为 `kind=web` 子策略 | MIT；77k⭐ 活跃 |
| **Midscene.js** | 跨端视觉自动化（iOS/Android/HarmonyOS/桌面/Web） | 作为 Playwright locator 失败时的 fallback | MIT；字节 Web Infra |
| **TestZeus Hercules** | Gherkin → E2E Agent；LangGraph planner / executor | ⚠️ **硬门禁（batch-275 M-16）**：采用前必须经**法务书面评估**（AGPL-3.0 对闭源商业分发 / SaaS 网络服务源码披露义务）；评估不通过或 SaaS 化计划在 1 年内触发 → **直接从候选清单剔除，不走 PoC**。评估通过且仅在完全隔离的独立服务中使用时方可 PoC。 | AGPL-3.0 |
| **ReportPortal** | 失败 ML Auto-Analysis（Product Bug / Automation Bug / System Issue） | 可选投影，非主平台事实源 | Apache 2.0；26.0.3+ 接 Agentic Results |
| **Allure Report** | 多语言静态报告 | 可选导出 | Apache 2.0 |
| **Wopee MCP** | SaaS crawl / 生成测试工件 | 仅做竞品验证；接受外部 SaaS + 数据出境 + 费用后再评估 | 需 UUID/Key |
| **QA Agent** (billrichards) | 轻量 Web 探索 | 低成本 PoC；JSON 导出后由平台导入 | MIT；范围窄 |
| **WarrDoge/Test-Agent** | 参考 Manifest/Skills/DAG 组织方式 | ⚠️ 1 star / 0 fork / 无 release，**提高准入门槛**；仅作代码审计参考 | README MIT |
| **vostride/agent-qa** | NL Web/Mobile QA harness / 运行事件理念 | 仅技术参考 | FSL-1.1-ALv2 + Early stage |

### 14.2 为什么不直接引入"大而全的 Test Agent"

1. 不同项目的数据模型/执行模型不同 → 直接搬入形成**第二套** Run/Case/Defect/Project/Auth。
2. 部分项目重点是探索操作，不是稳定的确定性回归。
3. 许可证差异可能影响闭源商业分发（特别是 AGPL）。
4. 运行时技术栈冲突：CamelTv 是 Python/FastAPI/React，TesterArmy 是 Node/TS，TestZeus 是 Python + LangGraph 依赖较重 → 用 **Runner Adapter 进程隔离**更安全。
5. AI 自称"测试成功"**不能代替** CamelTv Acceptance Criteria 的机器断言 + 证据。

### 14.3 统一 OSS 准入检查表（12 项）

每个外部仓库固定以下信息，**未全通过不得进入生产**：

```yaml
oss_admission:
  - git_url + commit_sha + tag + release_date + maintainer_activity
  - LICENSE + NOTICE + SBOM + 传递依赖许可证
  - CVE / 安全公告 / 供应链扫描结果
  - 支持 OS / CPU / Python / Node / Browser 版本
  - 可离线/自托管能力
  - 是否上传截图/DOM/HAR/用户数据到云端
  - API 稳定性 / 数据输出协议 / 错误退出码
  - 并发控制 / 取消 / 超时 / 资源清理
  - 身份凭据如何注入 / 日志是否泄密
  - 是否可以只用执行引擎而不引入其项目管理/用户/DB
  - CamelTv Adapter 的 contract tests 是否通过（§7.5）
  - 供应商条款 / 数据出境 / 费用
```

### 14.4 PoC 选择矩阵（第一轮 2 周）

| PoC | 场景 | 通过条件 | 失败回退方案（batch-276 M-18） |
|-----|------|---------|------------------------------|
| **Playwright MCP** | 登录 → 导航 → 检查前台赛事实体页 | 操作可审计；权限隔离；输出 A11y/DOM；不能访问未授权域名 | 回退现有 Playwright Runner 内置 locator（TA-013）；"AI 探索模式"本阶段不接，不影响主链路 |
| **TesterArmy e2e** | 一个现有 CamelTv 业务流程混合 agent.act + expect | 固定版本可靠完成 + 重放；导出 trace/artifact 能被 Adapter 收集；不依赖云 SaaS 完成基础场景 | 回退**纯 Playwright**（TA-013 扩展）；不引入外部 agent 执行器，Workflow 编排仍由 §6 DAG 承担 |
| **Keploy** | 捕获一个 Test5 API 依赖链 + 隔离一个不稳定第三方 API | 录制 + 隔离环境重放；DB/消息录制范围 + 脱敏通过；eBPF 部署限制已评估 | 回退**手写 mock/fixture + HTTP Driver**（TA-012）；录制能力降级为 V1.1+ 可选项 |
| **TestZeus Hercules** | Gherkin → E2E → 证据 | **先决条件（batch-275 M-16）**：法务书面评估完成且结论为"可采"。满足后 PoC 通过条件：AGPL 隔离部署方案成立 + 依赖安全 + Playwright 兼容 + 输出映射通过。**法务未通过前不启动 PoC**。 | **直接删除候选**（法务不通过 / 隔离方案不成立）；Gherkin 输入由 TA-009 Workflow Validator 自研承接 |

**回退不是失败**：任一 PoC 不通过即按上表回退，**不阻塞 M2 开工**；回退决策记录进 `work-logs/` 与对应 ADR，PoC 结论必须写"通过 / 回退 / 删除候选"三态之一，不允许"待定"。

**原则**：**不以 stars 为唯一标准**；以可运行性 / 最近维护 / 许可证 / 可观察性 / 可靠复现 / 适配成本为标准。

### 14.5 Adapter 契约（统一输出结构）

```json
{
  "adapter_key": "tester_army_e2e",
  "adapter_version": "0.1.0",
  "external_engine": "e2e",
  "external_run_id": "engine-run-123",
  "camel_run_id": "uuid",
  "status": "completed",
  "started_at": "2026-11-09T01:00:00Z",
  "finished_at": "2026-11-09T01:02:30Z",
  "events": [],
  "assertions": [],
  "artifacts": [],
  "raw_result_ref": "artifact://..."
}
```

**能力映射硬规则**：

- 外部 `passed/failed/skipped` 映射到 CamelTv node/assertion 状态；
- 外部 retry **不覆盖**首次失败；
- 外部 locator repair 只能生成**建议/新草案**，不能静默改已审核脚本；
- 外部报告附件必须经过大小限制 / 脱敏 / 内容安全扫描后入库；
- 外部工具无法提供某类事件时，明确标记 `unsupported`，**不造假补字段**。


---

## §15 REST / MCP API 契约

### 15.1 前缀与命名

- REST 统一前缀：`/api/v1/aiqe/`（避开现有 `/api/v1/*` 路由冲突；TA-004 审计后可回退到现有命名）。
- 所有写操作支持 `Idempotency-Key` header（防重）。
- 返回统一包装：`{ "data": ..., "meta": { "trace_id": "...", "request_id": "..." } }`。
- 错误体统一：`{ "error": { "code", "message", "details", "correlation_id" } }`。

### 15.2 REST 清单

**现状对齐**（batch-278，详见 [`docs/aiqe/baseline.md`](../aiqe/baseline.md) §7）：现有 `/api/v1/*` 实测 **265 paths / 323 operations**（27 个业务段）；下表 30 个 AIQE 端点中只有 `POST /test-cases/{id}/review` 可直接复用，其余 **29 个为净新增**。

#### 需求契约

| Method | Path | 用途 |
|--------|------|------|
| POST | `/projects/{project_id}/requirement-contracts` | 建立契约草案 |
| POST | `/requirement-contracts/{id}/analyze` | A1 解析/补齐歧义 |
| GET | `/requirement-contracts/{id}` | 详情 |
| POST | `/requirement-contracts/{id}/freeze` | 人工冻结版本 |
| POST | `/requirement-contracts/{id}/diff?against={version}` | 版本差异 |

#### 用例 / 场景

| Method | Path | 用途 |
|--------|------|------|
| POST | `/test-scenarios/generate` | A2 按契约生成场景/用例草案 |
| GET | `/test-scenarios/{id}` | — |
| POST | `/test-cases/{id}/review` | A2 Reviewer 评审 |
| GET | `/test-cases/{id}/coverage` | 覆盖矩阵 |

#### Workflow

| Method | Path | 用途 |
|--------|------|------|
| POST | `/workflows/plan` | A3 生成 DAG 草案 |
| POST | `/workflows/{id}/validate` | 静态校验 + Driver 能力校验 |
| POST | `/workflows/{id}/approve` | 人工批准冻结 |
| GET | `/workflows/{id}` | — |

#### Runs

| Method | Path | 用途 |
|--------|------|------|
| POST | `/runs` | 创建 Run（`Idempotency-Key` 必填） |
| GET | `/runs/{id}` | 摘要 |
| GET | `/runs/{id}/events?after_seq=N` | SSE 事件补拉 |
| GET | `/runs/{id}/graph` | DAG 节点状态 |
| GET | `/runs/{id}/nodes/{node_id}` | 节点详情 |
| GET | `/runs/{id}/nodes/{node_id}/attempts` | 尝试历史 |
| GET | `/runs/{id}/artifacts` | Artifact 清单 |
| GET | `/runs/{id}/live-frame` | 最新缩略图 |
| GET | `/runs/{id}/compare?against={other_id}` | 回归对比 |
| POST | `/runs/{id}/cancel` | 取消 |
| POST | `/runs/{id}/triage` | 创建/继续归因 |

#### Triage / Experiments

| Method | Path | 用途 |
|--------|------|------|
| POST | `/triage/{id}/experiments` | 创建对照实验（E1-E6） |
| GET | `/triage/{id}` | 详情 + 假设列表 |

#### 缺陷 / 回归

| Method | Path | 用途 |
|--------|------|------|
| POST | `/defects/{id}/regressions` | 一键回归 |
| GET | `/regressions/{id}` | 回归状态 + 对照 |

#### Learning

| Method | Path | 用途 |
|--------|------|------|
| POST | `/learning-candidates/{id}/approve` | 审核学习候选 |
| GET | `/learning-candidates?project_id=...` | 列表 |

#### MCP Gateway（供 Codex / ChatGPT / Cursor）

```text
mcp://cameltv-aiqe/
  tools:
    - run.get_summary       (read)
    - run.get_events        (read)
    - defect.list           (read)
    - defect.get            (read)
    - workflow.plan_draft   (write, token+audit)
    - run.create            (write, requires approval flag)
    - regression.create     (write, requires approval flag)
```

写能力必须走审批 + token 白名单。

### 15.3 创建 Run 请求/响应示例

```json
// POST /api/v1/aiqe/runs
{
  "workflow_definition_id": "uuid",
  "environment_id": "uuid",
  "execution_profile_id": "uuid",
  "build_ref": "test5-2026.11.09.3",
  "commit_sha": "40-hex-sha",
  "input_overrides": { "fixture.match_id": "fixture:generated_match" },
  "run_options": { "headed": false, "capture_trace": "on_failure", "max_parallel_nodes": 2 }
}
```

```json
// response
{
  "data": {
    "run_id": "uuid",
    "run_key": "RUN-20261109-00012",
    "status": "QUEUED",
    "events_url": "/api/v1/aiqe/runs/uuid/events",
    "graph_url": "/api/v1/aiqe/runs/uuid/graph"
  },
  "meta": { "trace_id": "...", "request_id": "..." }
}
```

### 15.4 Triage 决策请求

```json
// POST /api/v1/aiqe/runs/{id}/triage
{
  "decision": "NEEDS_EXPERIMENT",
  "hypotheses": [
    {
      "classification": "TEST_DATA_CONTAMINATION",
      "evidence_refs": ["artifact:uuid", "event:42"],
      "supporting_signals": ["same_user_id_used_by_parallel_run"],
      "contradicting_signals": [],
      "verification_plan": { "experiment": "E2", "change_only": "fixture_namespace" }
    }
  ],
  "human_review_required": true
}
```

### 15.5 错误与幂等

```json
{
  "error": {
    "code": "WORKFLOW_CAPABILITY_MISSING",
    "message": "当前执行节点不支持该 driver capability",
    "details": { "required": "playwright.chromium", "available": ["api.http"] },
    "correlation_id": "uuid"
  }
}
```

幂等键规则：

- `POST /runs`：`Idempotency-Key` header（client 重试不建重复 Run）；
- Node dispatch：`(run_id, node_key, attempt_no)`；
- Runner 上报事件：`(run_id, producer_event_id)` 或 `seq`；
- 证据上传：`(storage_uri, sha256)`；
- 回归：`(defect_id, fixed_commit_sha, selection_mode)` 重复请求保护（用户明确重复回归可产生新 request）。


---

## §16 安全与数据治理

### 16.1 凭据

- token / cookie / password / API key **只能存 Vault / Secret Manager 引用**；
- 控制面 DB 永远不落明文；
- `.env` 必须 `chmod 600`，不入 git；
- Runner 凭据从 Secret Manager 拉取 → 内存使用 → Run 结束清理。

### 16.2 证据脱敏

- HAR / DOM / 截图 / 视频在采集时 **inline 遮罩**：手机号 / 身份证 / 银行卡 / token / 密码 / 邮箱局部脱敏；
- Redaction 失败的 artifact `redaction_status=rejected` 不入库；
- 原始敏感内容如需保留 → 加密 + 更严格权限（审批日志）。

**实现选型（batch-276 D-4）**：

- **默认实现（V1）＝ 自写正则引擎，不引入 presidio**：把 `app/services/knowledge/sanitize.py` 已上线的规则集（鉴权头 / 裸 JWT / 敏感键值 / 手机号 / 邮箱 / 身份证）抽成独立模块 `app/aiqe/redaction/`，对外暴露 `RedactionEngine.redact(text|bytes, mime, scope) -> RedactionResult`；knowledge 入库与 Run 证据共用同一引擎，避免两套规则漂移；
- **规则外置 YAML**：`test-platform-v2/backend/app/aiqe/redaction/rules.yaml`（`schema_version: 1`；每条规则 `id / pattern / replace / applies_to(mime|field) / severity`）；改规则必须同时加 fixture 用例，PR 评审看 diff；
- **升级路径（V1.1+，需 ADR）**：只有出现"姓名 / 地址 / 自由文本 PII"这类 NER 级需求时才评估 `presidio`（依赖 spacy 模型，镜像体积与启动时间显著增加），且必须先过 §14.3 OSS 准入 12 项 + 独立 ADR，**不得直接替换默认引擎**；
- **明确不选**：`faker` / `faker-sensitive` 类库是"造数据"而非"脱敏"，输出不可回归比对，不作为实现；
- **验收**：TA-007 用 10 组真实 HAR / DOM 样本跑红队用例，`redaction_status=sanitized` 且无 PII 残留；误报率 / 漏报率与规则版本记录进 `docs/aiqe/ops.md`。

### 16.3 DB Driver 安全

- **只读事务**；
- 白名单 schema；
- 只能用**登记的 SQL Template**（不允许 LLM 生成任意 SQL 直接执行）；
- 参数绑定（SQLAlchemy `text() + bindparams`）；
- 最大行数 + 查询超时 + 结果脱敏；
- 生产 DB 默认禁用，除 `read_only` 环境外需特批。

### 16.4 生产环境

- 默认 **只读** + 有限采集；
- 不允许测试造数、破坏性动作；
- `assert_public_url()` 强校验；
- 支付 / VIP / 身份 / 风控 路径走**红线清单**，任何写操作必须显式特批。

### 16.5 Artifact 存取

- 下载 **签名 URL**，限时（默认 15 分钟）；
- 查看 / 下载 / 删除 **全链路审计**；
- Artifact 的权限继承 Run 的 project RBAC。

### 16.6 Agent 调用安全

- Agent 只能调用 `tool_registry.allowlist()` 返回的工具；
- 外部网页 / Issue / PR 文本视为**不可信数据**，不允许改变 System Prompt / 工具权限；
- Agent 输出的 URL / Query / SQL 入库前经过**白名单校验**；
- Agent 单次 token budget 限制（默认 32K prompt + 8K completion）；
- `token_budget` 超限自动截断 + 标记 `warnings`。

### 16.7 Secret Reference

```python
# app/aiqe/security/secret_refs.py
@dataclass
class SecretRef:
    scheme: str         # vault / env
    path: str
    version: str | None = None

    def resolve(self, ctx: RunContext) -> str:
        # 只允许在节点侧 resolve，控制面侧返回占位符
        if ctx.side == "control_plane":
            return "<redacted>"
        return self._backend().get(self.path, self.version)
```

事件 payload 中出现 SecretRef 不解引用，前端显示 `<redacted>`。

### 16.8 CI 安全守卫

- `scripts/ci/scan-common-bugs.ps1`：扩规则，禁止：
  - 裸 `eval() / exec() / subprocess shell=True`；
  - 裸 `os.getenv("...")` 直接 return（必须走 SecretRef）；
  - Alembic 迁移里的 `op.drop_table` 无 `IF EXISTS` 守卫；
  - `status_code == 404` 单独使用（延续 C86-1 双 404 约定）；
  - DB Driver 代码里 `.execute(f"...")` 字符串拼接。


---

## §17 项目适配器模板

### 17.1 接入新项目的 30 分钟清单

```yaml
# docs/standards/project-adapters/<project>.adapter.yaml
project: <project-key>
display_name: "..."

platforms:
  - { key: pc_web,              label: "PC 浏览器" }
  - { key: mobile_web,          label: "移动浏览器/H5" }
  - { key: miniapp,             label: "微信小程序" }
  - { key: android,             label: "Android 原生" }
  - { key: ios,                 label: "iOS 原生" }
  - { key: api,                 label: "接口" }

# 页面源（四源交叉：crawl + source + mp app.json + PRD）
pages:
  source: file
  path: ./pages/<project>-pages.json
  default_platform: pc_web
  kind_keywords:
    list_page:   ["列表", "home", "feed"]
    detail_page: ["详情", "detail"]

# 接口源
interfaces:
  source: openapi
  path: ./openapi/<project>.yaml
  default_domain: core
  domain_map:
    - { name: live,    prefixes: ["/live/*", "/event/*"] }
    - { name: user,    prefixes: ["/user/*", "/auth/*"] }
    - { name: payment, prefixes: ["/pay/*"] }

# 环境连接 slot（节点读 .env，控制面不存）
environment_slots:
  mysql:  { host_env: CAMELTV_TEST_DB_HOST,  user_env: CAMELTV_TEST_DB_USER, pwd_env: CAMELTV_TEST_DB_PWD }
  redis:  { host_env: CAMELTV_TEST_REDIS_HOST, pwd_env: CAMELTV_TEST_REDIS_PWD }
  mongo:  null
  kafka:  null
  api_base: { env: CAMELTV_TEST_API_BASE }

# 跨端链路闭包（admin ↔ consumer）
business_closures:
  - id: EVENT-PUBLISH-TO-CONSUMER
    name: "赛事上架到 C 端可见"
    chain: [admin_create, admin_publish, data_state, api_list, mobile_web_show, miniapp_show]

prompt_profile_path: ./cameltv-sports.prompt-profile.yaml
capabilities_path:   ./cameltv-sports.capabilities.yaml
```

### 17.2 Capabilities 文件（节点实测驱动）

```yaml
# docs/standards/project-adapters/<project>.capabilities.yaml
capabilities:
  - id: web
    available: true
    evidence: { last_pass_run_id: "RUN-20261109-00031", last_pass_at: "..." }
  - id: mobile_web
    available: true
    evidence: { ... }
  - id: miniapp
    available: false
    reason: "无 weapp-dev-mcp 节点"
  - id: android
    available: false
    reason: "无真机池"

page_requirements:
  by_platform:
    pc_web:
      - R01   # 可发现性
      - R07   # 文本容器溢出
      - R21   # 对比度
      - R22   # 响应式
      - R23   # 键盘焦点
    mobile_web: [R01, R07, R21, R22]
    miniapp: [R01, R07]

chain_requirements:
  default:
    - R12   # IDOR
    - R13   # 后台到终端
    - R14   # 异步任务
  by_domain_keyword:
    live: [R19]   # 并发一致
    payment: [R14, R19]
```

### 17.3 Prompt Profile（项目相关 context，L1 规则**不在此**）

```yaml
# docs/standards/project-adapters/<project>.prompt-profile.yaml
glossary:
  - term: "直播间"
    aliases: ["live_room", "room"]
  - term: "赛事"
    aliases: ["match", "event"]

references:
  case_design:
    - tests/test-case-standards/体育平台-关联基座.json
  triage:
    - work-logs/evidence/batch-269/*.md

bug_pattern_digest_path: .claude/skills/bug-pattern-curator/references/<project>/digest.md
```

### 17.4 已有适配器现状

| 项目 | adapter.yaml | capabilities | prompt_profile | 状态 |
|------|-------------|-------------|---------------|------|
| `futurewayu` | ✅ 5 platforms | ✅ | ⚠️ 需从 augmenter SKILL.md 搬出 | 进行中 |
| `cameltv-sports` | ⚠️ 仅 api 1 platform | ⚠️ | ⚠️ | **A5-4 补齐** |


---

## §18 代码骨架与开发约定

### 18.1 后端目录（**审计后再创建**）

```text
test-platform-v2/backend/app/
  aiqe/
    __init__.py
    api/
      runs.py
      workflows.py
      triage.py
      regressions.py
      agent_tasks.py
      artifacts.py
      events.py               # SSE endpoint
    models/
      run.py
      workflow.py
      event.py
      artifact.py
      triage.py
      regression.py
      agent_execution.py
      interference.py
      noise_rule.py
      profile.py
      target_env.py
      node_manifest.py
      requirement_contract.py
      acceptance_criterion.py
    schemas/
      workflow.py
      run.py
      event.py
      assertion.py
      triage.py
      agent.py
    services/
      run_service.py
      run_state.py            # 状态机单入口
      workflow_validator.py
      dag_scheduler.py
      run_context.py          # 变量/secret ref 存储
      event_service.py        # outbox 事务
      artifact_service.py
      assertion_service.py
      triage_service.py
      regression_service.py
      interference_service.py
      noise_rule_service.py
      capability_registry.py
    drivers/
      base.py
      registry.py
      httpx_driver.py
      playwright_driver.py
      db_readonly_driver.py
      event_driver.py
      external_e2e_driver.py
      keploy_driver.py
      mobile_web_driver.py
      miniapp_driver.py
      appium_driver.py
      midscene_driver.py
    agents/
      base.py
      orchestrator.py
      requirement_agent.py
      test_design_agent.py
      workflow_planner_agent.py
      failure_triage_agent.py
      change_impact_agent.py
      learning_curator_agent.py
      noise_hint_agent.py
      prompts/
      evals/
    security/
      redaction.py
      permission_policy.py
      secret_refs.py
    workers/
      dispatch.py
      event_consumer.py
      artifact_worker.py
      outbox_dispatcher.py
```

**关键**：如果 TA-001 审计发现已有 `app/services/xxx_service.py` 对应同职责，**扩展现有文件**而不是在 `aiqe/services/` 下新建同义文件。

### 18.2 前端目录

```text
test-platform-v2/frontend/src/
  pages/                          # 沿用现有 19 个域目录（153 个页面组件）
    runs/
      RunListPage.tsx
      RunDetailPage.tsx
      RunComparePage.tsx         # 回归对比
      components/
        RunHeader.tsx
        RunGraph.tsx             # DAG 可视化
        RunTimeline.tsx          # SSE 事件时间线
        StepDetailPanel.tsx
        AssertionDiff.tsx
        ArtifactViewer.tsx       # 通用证据查看
        LiveFrame.tsx            # 节点实时缩略图
        PlatformMatrix.tsx       # 跨端对照
      hooks/useRunEvents.ts
      api.ts
      types.ts
    triage/
      TriagePage.tsx
      components/
        HypothesisList.tsx
        ExperimentPanel.tsx      # E1-E6 对照
        EvidenceTimeline.tsx
    regressions/
      components/
        RegressionDialog.tsx
        RunComparison.tsx
    workflows/
      WorkflowListPage.tsx
      WorkflowDetailPage.tsx     # 可视化 + approve
    requirement-contracts/
      RequirementContractPage.tsx
    profiles/
      ExecutionProfilePage.tsx
```

**目录决策**（batch-278 D-278-3）：现有 `frontend/src/pages/` 已按域分 **19 个目录 / 153 个页面组件**（`version-tasks`、`testcase`、`apitest`、`uitest`…），**沿用该结构**，新增 `pages/runs`、`pages/triage`、`pages/regressions`、`pages/workflows`、`pages/requirement-contracts`、`pages/profiles`；**不新建 `features/`**（会形成两套导入路径）。通用组件下沉 `src/ui/`，页面级组件留在各自 `pages/<domain>/components/`。

**路由决策**（batch-276 D-6）：

- **保留 `/version-tasks` 作为业务入口**：现有 `frontend/src/router/index.tsx` 已挂 `version-tasks`、`version-tasks/new`、`version-tasks/:taskId`，继续承载"版本任务 → 执行 → 报告"的业务语义；
- **新增 `/runs` 作为通用 Run 列表**：`/runs`、`/runs/:runId`、`/runs/:runId/compare`，服务 `source_type = manual / defect_regression / pr / github_action / schedule / agent` 等非版本任务来源的 Run；
- **详情页组件复用**：`RunHeader / RunGraph / RunTimeline / ArtifactViewer / useRunEvents` 只实现一份；`/version-tasks/:taskId` 在 M1 迁到同一套组件（URL 与业务交互不变）；
- **兼容**：不删除现有 `version-tasks` 路由；M4 起版本任务列表可跳转 `/runs/:runId` 看通用 Run 详情；
- **导航去重**：侧边栏只加"Run 中心"一个入口，不把 `/runs` 与"版本任务"并列成两个执行入口。

### 18.3 Pydantic schema 骨架

```python
# app/aiqe/schemas/run.py
from datetime import datetime
from enum import StrEnum
from typing import Any, Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field

class RunStatus(StrEnum):
    DRAFT = "DRAFT"
    VALIDATING = "VALIDATING"
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    WAITING_HUMAN = "WAITING_HUMAN"
    TRIAGING = "TRIAGING"
    COMPLETED = "COMPLETED"
    BLOCKED = "BLOCKED"
    CANCELED = "CANCELED"
    ERROR = "ERROR"

class RunOutcome(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    INCOMPLETE = "INCOMPLETE"
    UNKNOWN = "UNKNOWN"

class EventCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    event_id: UUID
    run_id: UUID
    node_key: str | None = None
    step_key: str | None = None
    attempt_no: int | None = Field(default=None, ge=1)
    event_type: str
    occurred_at: datetime
    producer: str
    producer_event_id: str
    correlation_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)

class RunCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    workflow_definition_id: UUID
    environment_id: UUID
    execution_profile_id: UUID
    build_ref: str = Field(min_length=1, max_length=255)
    commit_sha: str | None = Field(default=None, min_length=7, max_length=64)
    input_overrides: dict[str, Any] = Field(default_factory=dict)
    run_options: dict[str, Any] = Field(default_factory=dict)
```

### 18.4 RunContext / Variable Store

```python
# app/aiqe/services/run_context.py
class RunContext:
    def __init__(self, run_id: UUID, project_id: UUID, profile: ExecutionProfile, side: Literal["control_plane","node"]):
        self.run_id = run_id
        self.project_id = project_id
        self.profile = profile
        self.side = side
        self._vars: dict[str, Any] = {}
        self._secrets: dict[str, SecretRef] = {}

    def set_output(self, node_key: str, key: str, value: Any) -> None:
        # 下游依赖节点才能读；写盘脱敏
        self._vars[f"nodes.{node_key}.outputs.{key}"] = redact_if_sensitive(value)

    def resolve(self, expr: str) -> Any:
        # 仅支持 ${nodes.X.outputs.Y} 这种受限语法，禁用任意表达式
        return resolver.resolve(expr, self._vars)
```

### 18.5 现有代码接入点（**基于 §0 审计前的已知**）

| 目标能力 | 现有文件 | 扩展方式 |
|---------|---------|---------|
| LLM 直连 | `app/services/ai_client.py` + `ai_config_service.py` | 保留，删除 `ai_gateway/` |
| Skill 注入 | `app/services/ai_service.py::_load_skill_context_for()` | 改为按项目 profile 动态加载 |
| 需求导入 | `app/services/requirement_service.py` + `openapi_import_service.py` | 加 `requirement_contract` 版本 + checksum |
| Playwright 执行 | `app/services/playwright_executor.py`（P0-4 迁出控制面） | 移到 `scripts/node/cameltv_node/drivers/` |
| 证据 | `app/services/evidence_bundle_service.py` | 加 Artifact / RunEvent 关联 |
| 缺陷 | `app/services/defect_service.py` | 加结构化字段 + `retest` 方法 |
| 节点协议 | `app/modules/campaign_execution/contracts.py` | 扩 `ExecutionJobKind` 枚举 |
| 节点运行时 | `scripts/node/cameltv_node/` | 装 Playwright 1.56 Agents / Midscene / Appium |

### 18.6 Event Outbox 处理顺序

1. Worker 上报 event；
2. `event_service.append_event()` 检查 `producer_event_id` 幂等；
3. **同一 DB 事务**内：取 `next_seq` → 写 `run_events` → 写 `event_outbox` → 投影 `node_runs / step_attempts`；
4. 事务提交；
5. `outbox_dispatcher` 推送 SSE / Redis PubSub；
6. 消费端按 `event_id` 去重。

**绝不"先 WebSocket，后 DB"**，否则浏览器看到的执行过程可能无法复现。


---

## §19 阶段开发任务（TA-001 … TA-045）

> **工期口径**：5-6 名工程人员（1 TL + 2 后端 + 1 前端 + 1 Runner/自动化 + 1 AI/平台，DevOps/QA 共享）。MVP 约 8-10 周，V1 (Web/API/DB) 16-20 周。
> **每个 TA 必须满足 §22 Definition of Done**。
> **优先级档（batch-276 M-20）**：`MVP` = M0-M2 必需；`V1` = M3-M6 补齐；`V1.1+` = 可延后到 V1 之后。每张 TA 表的最后一列即裁剪依据：**MVP 未全绿不得启动 V1.1+ 任务**；2-3 人团队按 §23 放大线执行，优先保 MVP。

### Phase 0（第 1-2 周）：代码审计 + OSS 准入 + P0

| ID | 任务 | 责任 | 文件 | 验收 | 优先级档 |
|----|------|------|------|------|------|
| **TA-000** | P0 阻塞清零（§0） | DevOps + TL | `production.env`、迁移、`scripts/ci/check-p0-ready.ps1` | P0-1..5 全部拿证据；CI 守卫通过 | MVP |
| **TA-001** | 当前执行链审计 | TL + 后端 + Runner | 产出 `docs/aiqe/baseline.md` | 实际 VersionTask → ExecutionJob → Node → Runner → Artifact 时序图；状态/心跳/取消/错误路径标注 | MVP |
| **TA-001.5** | P0 守卫脚本 | DevOps | `scripts/ci/check-p0-ready.ps1` | 跑脚本返回 0 当且仅当 P0-1..5 全绿 | MVP |
| **TA-002** | OSS SBOM/License 准入 | Runner + DevOps | `docs/aiqe/oss-adoption-register.md` | 10 个候选项目每个 fixed commit + LICENSE + CVE 扫描；未批准不入 image | MVP |
| **TA-003** | Test 环境就绪 | DevOps + 后端 | `deploy/`、test adapter | Test env 对生产 DB/凭据零写权限；Run 只在允许环境执行；健康检查失败 → `BLOCKED` | MVP |
| **TA-004** | ADR + 模型映射表 | TL + 后端 | `docs/aiqe/model-mapping.md`、`docs/adr/0031..0038-*.md` | 本规格每张表 → 现有类/表/路由/组件 映射表；无同义重复 | MVP |
| **TA-004.2** | JSON schema CI 守卫 | 后端 | `scripts/ci/check-json-schema-version.ps1` | 所有 JSON 字段必须有 schema_version + Pydantic 校验；无就拒 PR | MVP |

### Phase 1（第 3-4 周）：Run / Event / Artifact 底座

| ID | 任务 | 责任 | 文件 | 验收 | 优先级档 |
|----|------|------|------|------|------|
| **TA-005** | Run 模型 + 状态机 | 后端 | `aiqe/models/run.py`、`services/run_state.py`、Alembic | 合法转换单测全绿；非法转换抛异常；旧 ExecutionJob 能关联 run_id | MVP |
| **TA-006** | Run Event Collector（Outbox） | 后端 | `aiqe/services/event_service.py`、`models/event.py` | 1000 事件 seq 无重复；worker 重发同 producer_event_id 不入库；事件 + 投影在同事务 | MVP |
| **TA-007** | Artifact Manager | 后端 + DevOps | `aiqe/services/artifact_service.py`、对象存储适配 | 图/trace 上传下载；越权 403；同 hash 去重；redaction_status 全链路 | MVP |
| **TA-008** | React Run Console MVP | 前端 | `features/runs/pages/RunListPage.tsx`、`RunDetailPage.tsx`、`useRunEvents.ts` | 刷新后状态 + 事件不丢；Run 完成可回放；SSE 断线补拉 | MVP |

### Phase 2（第 5-7 周）：DAG + Driver + 变量传递

| ID | 任务 | 责任 | 文件 | 验收 | 优先级档 |
|----|------|------|------|------|------|
| **TA-009** | Workflow Schema / Validator | 后端 | `aiqe/services/workflow_validator.py`、`models/workflow.py` | 循环依赖 / 未注册 Driver / 悬空变量 / 非幂等重试全部被拒 | MVP |
| **TA-010** | DAG Scheduler | 后端 | `aiqe/services/dag_scheduler.py`、`workers/dispatch.py` | 串行/并行/失败阻断/条件分支通过；Worker 重启可恢复；资源锁带 fencing token | MVP |
| **TA-010.3** | 资源锁（fencing token） | 后端 | `aiqe/services/resource_lock.py` | 7 粒度锁 + TTL + heartbeat；Worker 崩溃后锁自动释放 | MVP |
| **TA-011** | RunContext / Variable Store | 后端 | `aiqe/services/run_context.py` | 动态变量跨节点传递；secret ref 不落明文；Run scope 隔离 | MVP |
| **TA-012** | HTTP Driver Adapter | 后端 | `aiqe/drivers/httpx_driver.py` | 多接口链真实执行；request/response 证据完整；首次失败不被 retry 覆盖 | MVP |
| **TA-013** | Playwright Driver Adapter | Runner | `scripts/node/cameltv_node/drivers/playwright_driver.py` | 后台登录 + 配置实体 + 前台查询 全链路同 Run 执行；trace / dom / a11y / console 齐全 | MVP |
| **TA-014** | DB Read-only Assertion Driver | 后端 + Runner | `aiqe/drivers/db_readonly_driver.py` | SELECT 通过；INSERT/UPDATE/DELETE/DDL 全被拒；行数超限 → 错误 | MVP |
| **TA-015** | Driver Registry + Capability | 后端 | `aiqe/services/capability_registry.py` | 节点自描述 + 实测 evidence；缺 WebKit 的 Node 不会收到 WebKit 任务 | MVP |

### Phase 3（第 7-10 周，并行）：OSS PoC + Agent 接入

| ID | 任务 | 责任 | 文件 | 验收 | 优先级档 |
|----|------|------|------|------|------|
| **TA-016** | Playwright MCP Explorer PoC | AI + Runner | `scripts/node/cameltv_node/mcp/playwright_mcp/` | AI 定位测试页输出 DOM/A11y + 动作日志；越权域名被拒 | V1 |
| **TA-017** | TesterArmy e2e Adapter PoC | Runner | 独立 Node Runner image + `aiqe/drivers/external_e2e_driver.py` | 固定版本执行 + 二次重放；trace/artifact 转 CamelTv 格式；退出码与 assertion 一致 | V1 |
| **TA-018** | Keploy Record/Replay PoC | Runner + DevOps | `aiqe/drivers/keploy_driver.py` | 录制 1 条上下游依赖；回放稳定；脱敏通过；eBPF 权限审计完 | V1 |
| **TA-019** | Agent Service + A0/A1 | AI + 后端 | `aiqe/agents/base.py`、`orchestrator.py`、`requirement_agent.py`、`agent_executions` 表 | 30 份需求评估集；AC 有来源引用；schema 错拒；Key 无效 fail-closed | V1 |
| **TA-020** | A2 Test Design / Review | AI | `aiqe/agents/test_design_agent.py` | 50 份需求评估集；P0 无验收断言不得批；旧用例覆盖充分时不重复新增 | V1 |
| **TA-020.3** | Oracle 来源守卫 CI | DevOps | `scripts/ci/check-oracle-layer.ps1` | assertion 缺 `oracle_layer` 全部拒 PR | V1 |
| **TA-021** | A3 Workflow Planner | AI + 后端 | `aiqe/agents/workflow_planner_agent.py` | 20 个已标注业务工作流依赖关系正确；未批准不能执行 | V1 |

### Phase 4（第 10-13 周）：失败归因 + 噪音治理 + 回归

| ID | 任务 | 责任 | 文件 | 验收 | 优先级档 |
|----|------|------|------|------|------|
| **TA-022** | Execution Profile / 数据隔离 | 后端 | `aiqe/models/profile.py`、`services/run_service.py` | `core_isolated / integration / external_live` 三档；两个并发 Run 无法误改同一共享 fixture；profile checksum 可复现 | V1 |
| **TA-023** | Interference Detectors | 后端 + Runner | `aiqe/services/interference_service.py` + 节点侧 detectors | 10 类预置故障检测信号正确；检测本身不改 Run 状态 | V1 |
| **TA-024** | A4 Failure & Triage Agent | AI + 后端 | `aiqe/agents/failure_triage_agent.py` | 100 标注样本（§21.4）；未知归因返 `UNKNOWN`；不凭模型 confidence 自动关缺陷 | V1 |
| **TA-024.2** | Noise Hint Agent（§10.4 Skill） | AI | `.claude/skills/noise-hint-agent/SKILL.md` | 对真实"广告抖动"样本输出疑似 hint + 证据引用 | V1 |
| **TA-025** | Counterfactual Replay Coordinator | 后端 | `aiqe/services/triage_service.py::run_experiment()` | E1-E6 每个单变量实验落 verification_run_id；双变量实验被拒；幂等检查通过 | V1 |
| **TA-026** | Defect Draft + Link | 后端 + 前端 | `defect_service.py`（扩）、`frontend/src/pages/defect/*` | 失败一键转缺陷带结构化复现步骤 + 证据跳转；详情页展示 linked_execution + AC | V1 |
| **TA-027** | 一键回归 | 后端 + 前端 | `POST /defects/:id/regressions`、`<RegressionDialog />`、`<RunComparison />` | 制造 Bug → Run Fail → Defect Draft → 修复 SHA → 点回归 → 新 Run PASS；旧 Run 保留；对比视图可用 | V1 |
| **TA-027.3** | Noise Suppression Rules | 后端 + 前端 | `aiqe/services/noise_rule_service.py`、规则 CRUD 页 | 规则 90 天强制复核；永久 quarantine 被拒 | V1 |

### Phase 5（第 13-17 周）：跨端 + 学习 + 质量门禁

| ID | 任务 | 责任 | 文件 | 验收 | 优先级档 |
|----|------|------|------|------|------|
| **TA-028** | Platform Acceptance Matrix | 前端 | `<PlatformMatrix />` | 同 AC 对应多端 Binding；每端独立 build/device/profile/actual/evidence；跨端语义类型展示 | V1 |
| **TA-029** | A5 Change Impact | AI + 后端 | `aiqe/agents/change_impact_agent.py` | PR diff → 候选回归并集强制 suite；公共权限/登录变化时强制用例不漏选 | V1 |
| **TA-030** | A6 Learning Curator | AI | `aiqe/agents/learning_curator_agent.py`、`learning_candidates / bug_patterns` 表 | 候选规则 → benchmark 评估 → 人审 → ACTIVE；误报/重复增加不能无提示发布 | V1 |
| **TA-031** | VersionTask Quality Gate | 后端 + 前端 | `aiqe/services/quality_gate.py`、版本任务详情页 | P0 未执行/未知/失败 → 门禁不显示 PASS | V1 |
| **TA-032** | MCP Gateway | 后端 | `scripts/mcp-server/aiqe_mcp/` | Codex 可查 Run；写动作需审批；三类外部 Agent 能从 Skill + MCP 合作 | V1 |
| **TA-032.5** | Agent Skills 开放标准封装 | AI + 平台 | `.claude/skills/<agent-key>/SKILL.md` × 6 | Claude Code / Codex / Cursor 三处加载同一 skill 跑通，截图存证 | V1 |

### Phase 6（第 17-20 周）：硬化 + 生产试点

| ID | 任务 | 责任 | 文件 | 验收 | 优先级档 |
|----|------|------|------|------|------|
| **TA-033** | Reliability + Security Hardening | DevOps + 后端 | 压测脚本 / Worker 故障注入 | 强杀 Worker 后 Run 可恢复或受控失败；不产生重复扣款 / 造数；RBAC 审计 | V1 |
| **TA-034** | CamelTv Sports 纵向验收 | QA + 后端 + Runner | `cameltv-sports` adapter 完整版 | TC-AIQE-001..010 全部通过；至少制造并修复一个真实缺陷 | V1 |
| **TA-034.2** | Asset-map 接入平台 | 前端 + 后端 | `aiqe/services/asset_map_integration.py` | 版本任务 step 2 展示页面地图；24 准则 assertion 结果进 EvidenceBundle；覆盖率三指标进判定页 | V1 |
| **TA-035** | 文档 / Ops / Rollback | TL + QA | `docs/aiqe/ops.md`、`docs/aiqe/rollback.md` | 新开发按文档可空环境起服务跑通最小 E2E；版本锁 + 升级/回滚脚本 | V1 |

### Phase 7（持续）：Agent 可移植

| ID | 任务 | 文件 | 验收 | 优先级档 |
|----|------|------|------|------|
| **TA-036** | 内网 MCP Server | `scripts/mcp-server/*` | Codex CLI 在公司网内 `mcp add cameltv-aiqe ...` 调通 | V1.1+ |
| **TA-037** | AGENTS.md 规整 | `AGENTS.md` | Codex 新 session 能读并按此行动 | V1.1+ |
| **TA-038** | Skill 跨 Agent 验证 | 任选 3 个 skill | Claude Code / Codex / Cursor 三处跑通 | V1.1+ |

### 预留扩展

| ID | 任务 | 描述 | 优先级档 |
|----|------|------|------|
| **TA-039** | Mobile Device Broker | 真机池管理（Android 优先，iOS 解 C84-1 后） | V1.1+ |
| **TA-040** | 小程序 Adapter | `minium` / `weapp-dev-mcp` 接入 + 微信版本兼容矩阵 | V1.1+ |
| **TA-041** | Desktop Driver | Electron / Windows UIA / AppleScript | V1.1+ |
| **TA-042** | 硬件 / IoT Driver | 单设备协议一套 Adapter | V1.1+ |
| **TA-043** | Domain Pack - E-commerce | future-wayu 项目接入 | V1.1+ |
| **TA-044** | Domain Pack - SaaS | Tenant/RBAC/Audit | V1.1+ |
| **TA-045** | Domain Pack - IoT | Device shadow / telemetry | V1.1+ |


---

## §20 E2E 验收场景（TC-AIQE-001 … 010）

> 必须在**隔离 Test 环境**运行；不能以 Mock-only、截图演示或 Agent 自述代替。

### TC-AIQE-001：需求契约冻结 + 需求变更影响

**前置**：导入"收藏赛事" PRD，含重复收藏、取消收藏、跨设备同步。

**执行**：
1. 上传 PRD/原型；
2. A1 Requirement Agent 提取 AC + open questions；
3. 人工确认一条歧义 + 其余 AC；
4. 冻结 Contract V1；
5. 编辑 PRD 新增"未登录点击收藏提示登录"；
6. 导入 V2 并分析影响。

**预期**：V1 checksum 不变；V2 差异列出；关联用例标记需复审；AI 不直接改 V1。

### TC-AIQE-002：API → Admin UI → Public API → DB 的统一 Run

**前置**：Test 环境健康；API/Playwright/DB-RO Driver 已注册；唯一 Fixture 模板。

**执行**：
1. 创建 Run；
2. API 创建赛事 → 输出 `match_id`；
3. Playwright 登录后台 → 按 `match_id` 配置直播源 → 发布；
4. Public API 查询状态；
5. DB 只读查询赛事 + 直播源关联；
6. 前台 Playwright 打开赛事页；
7. Cleanup 删除 Run 自己的数据。

**预期**：所有步骤同一 Run；`match_id` 动态传递；时间线可见请求/页面动作/断言；Artifact 可查看；任意步骤失败下游按 DAG 策略 `BLOCKED`；Cleanup 仍按策略执行。

### TC-AIQE-003：API 首次失败 + 重试成功 → 不得掩盖失败

**前置**：可注入一次 503 的 API Stub。

**执行**：第一次 503；retry policy 允许一次重试；第二次 200。

**预期**：两个 Attempt 都存在；Node 状态按策略最终 PASSED；时间线**明确显示** `attempt 1 FAILED + attempt 2 PASSED`；Triage 标 `FLAKY/transient candidate`；P0 用例的 Quality Gate 可按策略要求复核，**不能只显示绿灯**。

### TC-AIQE-004：广告/其他功能浮层造成交叉干扰

**前置**：直播入口按钮；integration profile 可注入浮层；core_isolated 关闭该 fixture。

**执行**：
1. Core Run 执行直播入口点击；
2. Integration Run 注入浮层 + 相同流程；
3. 采集 hit target / DOM / 截图 / Network；
4. 对照两次 Run。

**预期**：Core `PASS`；Integration `FAIL`；归因候选 `CROSS_FEATURE_DEFECT`；生成关联浮层功能的 Defect Draft。**不得**把 Integration 记为 `PASS`，也**不得**把它简单归到赛事服务代码错误。

### TC-AIQE-005：并发数据污染

**前置**：共享账号 / 赛事 fixture。

**执行**：Run A + Run B 同时改同一赛事状态。

**预期**：Scheduler 通过锁串行，或数据 namespace 自动隔离；若外部操作绕过锁造成污染，检测器关联两个 Run + 数据变更时间线，归因候选 `CONCURRENCY/TEST_DATA_CONTAMINATION`。

### TC-AIQE-006：上游第三方故障

**前置**：外部赛程接口可返回 504。

**执行**：运行依赖该接口的测试。

**预期**：检测到上游 504；相关 Node `BLOCKED/UPSTREAM`；本系统业务 Assertion 未执行时**不**创建 Bug；若真实产品必须处理 504 而没有降级 → 另用异常契约测试验证为产品缺陷。

### TC-AIQE-007：UI Runner 自身故障

**前置**：浏览器进程被强制 kill。

**执行**：页面动作中终止浏览器。

**预期**：Driver 上报 `AUTOMATION/WORKER_FAILURE`；业务断言记 `NOT_EVALUATED`，**不**假造产品 Bug；Node 不能无限 `RUNNING`；Run 有可读错误。

### TC-AIQE-008：开发修复后点击回归

**前置**：TC-AIQE-004 创建 Defect Draft 并人工确认；缺陷修复提交 commit SHA。

**执行**：部署指定 SHA 到 Test 环境；缺陷页点回归，选 Scenario + P0 smoke。

**预期**：创建新 `RegressionRequest` + 新 `TestRun`；旧 Run 仍可看；新 Run env_snapshot 包含 fixed SHA；对比 AC + Assertion；所有强制回归集都执行或明确 `BLOCKED`。

### TC-AIQE-009：多端 AC 对照

**前置**：同一业务意图绑定 PC Chrome + Android Chrome（模拟器/真机明确标识）。

**执行**：两端执行同一 AC。

**预期**：每端独立 build/device/profile/actual/evidence；Android 无可用设备 → `NO_DRIVER/BLOCKED`，不算通过；失败能具体指出哪端 / 哪 AC / 哪步 / 截图 / Trace。

### TC-AIQE-010：学习候选发布

**前置**：已确认一个"切换账号后旧用户数据残留"缺陷 + 对应回归修复。

**执行**：A6 Learning Curator 生成 BugPattern 候选；检查现有用例是否覆盖；跑 benchmark；人工批准。

**预期**：规则状态 `CANDIDATE → EVALUATING → REVIEW_REQUIRED → APPROVED → ACTIVE`；增加大量重复用例或误报时规则**不能**发布；旧 Run 仍引用原 Knowledge version。


---

## §21 Agent 评估基准集

> 每个 Agent 必须跑过对应 benchmark 才能发布。评估集位于 `test-platform-v2/backend/app/aiqe/agents/evals/`。

### 21.0 数据集准备（batch-275 D-9 补充 — **TA-001 并行子任务，不是 Agent 开工时才找**）

**强制规则**：Agent 评估集的数据收集**在 batch-278 TA-001 代码审计阶段并行启动**，不能等 M3 开工才临时拼凑。否则 Agent 开发会卡在"schema 跑通但没真实样本"阶段。

**A1 Requirement 的 30 份需求**：

- 从 `app/models/requirement.py` 现有数据抽样 15 份（覆盖清晰/歧义/冲突/非功能各类）；
- 从 `lanhu_evidence` 包抽 10 份（含原型）；
- 从历史 batch PRD 抽 5 份（`test-platform-v2/work-logs/batch-*-prd-*.md`）。

**A2 Test Design 的 50 份 PRD**：

- 从 `app/models/test_case.py` + `test_case_version.py` 已采纳用例中抽样 50 份作为"PRD → case"对照；
- 必须已有人工审核的 case 作为"黄金答案"。

**A4 Triage 的 100 标注失败样本**：

- 从 `app/models/defect.py` 历史真实缺陷 × 50 条（含修复 commit、分类标签）；
- 从 batch-274 评审期间收集的 M-* + D-* 条目 × 20 条（documentation defect）；
- 从 M4 Dogfood 7 类注入 + 对照实验 × 30 条（本 session 产生）。

**A5 Impact 的 20 PR**：

- 从 origin/main 近 100 PR 中挑 20 个带明确回归记录的（如 batch-240..273 的 PR）；
- 必须已有"本 PR 应跑哪些用例"的人工标签。

**数据集版本锁**：所有 benchmark 存 `test-platform-v2/backend/app/aiqe/agents/evals/<agent_key>/`，每份样本 YAML + schema_version + 来源 ref。

**数据集准备进度**（每周在 kanban 跟踪）：

- batch-278 结束时（W2）：A1 已 30/30，A2 已 25/50，A4 已 50/100；
- M2 结束时（W7）：A1 已 30/30，A2 已 50/50，A4 已 100/100，A5 已 20/20；
- M3 开工（W8）：100% 就绪。

### 21.1 A1 Requirement Assurance

**数据集**：30 份需求，覆盖：清晰 / 歧义 / 互相冲突 / 含原型 / 后续变更 / 非功能需求。

**指标**：
- `ac_source_traceability` ≥ 0.95（每条 AC 能回到源文件/章节）
- `ambiguity_recall` ≥ 0.80（已知歧义被识别的比例）
- `hallucinated_rules_count` = **0**（AI 编造的 business rule 必须 0）

### 21.2 A2 Test Design & Review

**数据集**：50 份已标注 PRD + 已有 BugPattern。

**指标**：
- `ac_coverage` ≥ 0.90（P0 AC 有对应 case）
- `duplicate_rate` ≤ 0.05（新增 case 与现有重复率）
- `executable_rate` ≥ 0.80（case 的 steps + assertions 可执行）
- 所有 P0 AI 生成 case **必须人工批准**才能进 case 库
- `bug_pattern_hit_rate` ≥ 0.70（历史 pattern 被引用覆盖的比例）

### 21.3 A3 Workflow Planner

**数据集**：20 条已人工绘制的 API + UI + DB 流程。

**指标**：
- `dag_dependency_correctness` ≥ 0.95
- `variable_reference_correctness` ≥ 0.95
- **Validator 必须拒绝所有无效 DAG**（0 假阳性）

### 21.4 A4 Failure & Interference Triage

**数据集**：100 个历史失败样本，标注：产品缺陷 / 跨功能 / 环境 / 上游 / 数据 / 并发 / 自动化 / 需求歧义 / flaky / 多因素。

**指标**：
- **`precision` 优先**（误归类成本高）：目标 ≥ 0.85
- `unknown_rate` ≥ 0.15（证据不足时能老实返 UNKNOWN）
- `hypothesis_count_median` ≥ 2（多假设）
- `experiment_validity` = 1.0（对照实验必须单变量）
- **不**使用 `accuracy` 做主指标（会鼓励盲猜）

### 21.5 A5 Change Impact

**数据集**：已知 Commit/PR + 实际回归记录。

**指标**：
- `recall` ≥ 0.90（应回归的用例被选中的比例）
- 公共组件变更 recall = 1.0（**强制**）
- `precision` ≥ 0.60（可容许多选，但不能漏）

### 21.6 A6 Learning Curator

**数据集**：每条已确认 Bug 至少能解释如何形成 pattern。

**指标**：
- `coverage_gain` > 0（新 pattern 进 benchmark 后相关用例覆盖提升）
- `duplicate_case_increase` ≤ 0.10（不能大量重复造例）
- `false_positive_increase` ≤ 0.05

### 21.7 评估驱动代码

```python
# app/aiqe/agents/evals/runner.py
async def run_eval(agent_key: str, dataset: Path, version: str) -> EvalReport:
    samples = load_samples(dataset)
    results = []
    for s in samples:
        req = AgentRequest(**s.input)
        res = await agent_service.invoke(req)
        results.append(score(s.expected, res))
    report = aggregate(results)
    if not report.passes_thresholds(THRESHOLDS[agent_key]):
        raise EvalFailed(f"Agent {agent_key}@{version} failed: {report}")
    write_report(report, agent_key, version)
    return report
```

CI 守卫（PR 合并前）：改 prompt / 工具 / 模型配置 → **必须跑对应 eval**；低于阈值阻断合入。


---

## §22 Definition of Done / 质量门禁

每个 TA Issue 必须满足：

1. **代码路径与迁移**：涉及 DB 必带 Alembic revision；可升可降。
2. **API schema / UI 页面 / Driver protocol** 更新 + 版本号。
3. **单元测试**：核心逻辑覆盖；状态机转换覆盖。
4. **集成测试**：至少一条真实业务链路。
5. **负向测试**：权限 / 超时 / 取消 / 异常路径 / 幂等。
6. **安全检查**：secret 不落日志；SQL/HTTP/subprocess 无注入面；RBAC 校验。
7. **可复现命令**：PR description 含"本地复现脚本"。
8. **真实输出 / Artifact**：screenshot / trace / log 至少一份入证据包。
9. **文档**：更新 README / ADR / architecture docs。
10. **Benchmarks / Eval**（Agent 类必须）：§21 对应评估集通过。
11. **PR 链接 + 固定 commit SHA**：便于复现。

**反例清单**（本文件会在 PR 模板中引用）：

- ❌ "接口写完" / "Agent 能回答问题" / "页面能打开" **不是**完成；
- ❌ "测试通过（截图 1 张）"**不是**证据——必须有 Run 的 artifact / event trail；
- ❌ "我本地跑过" **不是**验收——CI 必须复现；
- ❌ "后面补测试" **不是**合入理由；
- ❌ "Agent 自己判断通过" **不是** PASS——deterministic assertion 才算。

---

## §23 里程碑

| 里程碑 | 周 | 交付 |
|-------|----|------|
| **M0 Baseline Freeze** | 2 | P0 清零；代码审计；OSS 准入；Test 环境；核心 ADR |
| **M1 Observable Run** | 4 | Run/Node/Step/Event/Artifact 模型；Run Console SSE |
| **M2 First Mixed Workflow** | 7 | API + 后台 UI + 前台 API + DB 的 DAG 测试跑通 |
| **M3 Agent-Assisted Planning** | 10 | A1 需求 / A2 用例 / A3 Workflow 三 Agent + eval |
| **M4 Triage + Regression** | 13 | 11 类噪音治理 / 6 对照实验 / Defect 结构化 / 一键回归 |
| **M5 Cross-Platform + Learning** | 17 | 多端矩阵 / A5 Impact / A6 Learning / MCP Gateway |
| **M6 Production Pilot** | 20 | 硬化 + 安全 + 体育业务纵向闭环 + TC-AIQE-001..010 全绿 |

每个里程碑的进入条件 = 前一个里程碑的 DoD 全绿。

**团队规模换算**（batch-276 M-19，口径与 14 号排期 §2.1 一致）：

| 里程碑 | 5-6 人基准（周） | 2-3 人放大（周） |
|-------|----------------|-----------------|
| M0 | 2 | 3-4 |
| M1 | 4 | 5-7 |
| M2 | 7 | 8-13 |
| M3 | 10 | 14-19 |
| M4 | 13 | 20-25 |
| M5 | 17 | 26-32 |
| M6 | 20 | 33-40 |
| **MVP（M0-M2）** | **8-10** | **16-20** |
| **V1（M0-M6）** | **20** | **32-40（≈ ×2）** |

小团队不得靠"压缩 M0"省时间：M0 的 P0 清零 / 代码审计 / OSS 准入是后续所有里程碑的前提，只延长不缩短。

---

## §24 ADR 清单

> 本规格立即新增以下 ADR。每条 ADR 对应一个决策点，PR 评审时引用。

| ADR | 决策题目 | 推荐决策 |
|-----|---------|---------|
| **ADR-AIQE-001** | 是否自研整套 Agent Framework | **不自研**；现有 LLM provider pool 上做 typed Agent Service，开源 Agent 以 Adapter 接入 |
| **ADR-AIQE-002** | 是否重写 UI Runner | **不重写**；当前 Playwright Runner 为主，评估 e2e / Playwright MCP 适配 |
| **ADR-AIQE-003** | 是否引入独立 Workflow Engine | **第一阶段复用** ExecutionJob + worker，持久化 DAG scheduler；只有确认故障恢复/超大规模确需才评估 Temporal |
| **ADR-AIQE-004** | 是否以 ReportPortal/Allure 取代平台报告 | **不取代**；平台 Run/Evidence 是事实源，第三方仅投影 |
| **ADR-AIQE-005** | 噪音是否作为 PASS/SKIP | **否**；归因类别与执行结果分开，`NOISE_SUSPECTED / BLOCKED` 不计 PASS |
| **ADR-AIQE-006** | 是否允许 AI 自动关闭 Bug | **不允许**；AI 仅建议，缺陷关闭有固定规则 + 人审 |
| **ADR-AIQE-007** | DB 能否由 Agent 任意 SQL | **不允许**；登记连接 + 只读事务 + 参数化模板 + 超时/行数/脱敏 |
| **ADR-AIQE-008** | WorkflowDefinition vs AITDE 的区别 | WorkflowDefinition 是**人审 + checksum 锁定 + Validator 过关**的 DAG；AITDE 建模层（Mission/Contract/Scenario/Oracle）**不恢复**。护栏：Workflow 必须绑 scenario_id 和 contract_version；禁止平行建模实体；禁止 AI 临场改已批 Workflow；**新建带 checksum + approval_status 的实体必须在 PR 回答"AITDE 翻版自检"**（见本节末） |
| **ADR-AIQE-009** | Agent Skills 开放标准 vs 自定 skill 格式 | 采用 **Anthropic Agent Skills 开放标准**；跨 Claude/Codex/Cursor 可移植 |
| **ADR-AIQE-010** | 多端测试统一抽象 | **Platform Binding + Driver Adapter**；AC 保持平台无关，各端 workflow_ref 映射 |

**PR 模板强制问答（batch-276 M-12，ADR-AIQE-008 的落地护栏）**

任何新建"带 `checksum` + `approval_status`（或同义审批字段）"实体的 PR，description 必须逐条回答：

1. **本 PR 新建的实体是否是 AITDE `Scenario / Mission / Contract / Oracle` 的翻版？**（是 / 否）
2. 若"是"：列出与 AITDE 的字段级差异，并说明现有 `WorkflowDefinition`（或对应已批准实体）为什么无法承载。**未回答 = Block PR**；
3. 若"否"：给出与 11 号方案 §2 删除清单不冲突的证据（`rg` 命中 0 / 现有表无同义字段截图或命令输出）。

该问答同时写入 `.github/pull_request_template.md` 的"架构护栏"节；QA 在批次验收时逐 PR 检查，缺失即打回。


---

## 附录 A：开源组件版本锁

| 组件 | 版本 | 许可证 | 用途 |
|------|------|--------|------|
| Playwright | `1.56.x`（支持 Agents 起点） | Apache-2.0 | Web / Mobile Web / Desktop (Electron) |
| Playwright MCP | 最近 stable | Apache-2.0 | 探索模式 |
| TesterArmy e2e | 固定 release（PoC 决定） | Apache-2.0 | 可选 Web/Mobile Agent 执行器 |
| Appium | 最近 LTS | Apache-2.0 | Android / iOS 原生 |
| Appium MCP Server | 官方 pulsemcp | Apache-2.0 | MCP 包装 |
| Keploy | 最近 stable | Apache-2.0 | API 流量录制 |
| browser-use | 最近小版本 | MIT | 复杂浏览流 |
| Midscene.js | 最近小版本 | MIT | 视觉 UI fallback |
| minium | WeChat 官方版本 | 微信开发者协议 | 小程序 |
| weapp-dev-mcp | 最近版本 | 待确认 | 小程序 MCP |
| TestZeus Hercules | ⚠️ 不建议合入；仅隔离服务使用 | **AGPL-3.0** | 可能对分发有限制 |
| ReportPortal | 26.0.3+ | Apache 2.0 | 失败 ML 分类投影 |
| Allure | 最近 stable | Apache 2.0 | 可选静态报告 |
| DeepSeek / OpenAI / Qwen / Claude | API | — | LLM provider（OpenAI 协议） |

升级 / 回滚脚本见 `docs/aiqe/ops.md`（TA-035 产出）。

---

## 附录 B：术语表

| 术语 | 定义 |
|------|------|
| **AC** | Acceptance Criterion，验收标准，Given-When-Then |
| **Adapter** | 项目/工具的接入层：Project Adapter / Driver Adapter / Platform Adapter |
| **Attempt** | StepAttempt，一次步骤尝试，永不被覆盖 |
| **Capability** | Driver 声明支持的能力（如 `browser.chromium`） |
| **Checksum** | 规范化 JSON 的 SHA；approved 后不变 |
| **Contract** | RequirementContract，冻结版本的需求契约 |
| **DAG** | 已批准 Workflow 的有向无环图 |
| **DoD** | Definition of Done |
| **Driver** | 执行腿的统一接口（http/playwright/db-ro/...） |
| **Execution Profile** | `core_isolated / integration / external_live` 三档 |
| **Evidence** | Artifact + Event + AssertionResult 的集合 |
| **Fencing Token** | 资源锁的递增 token，防旧 Worker 继续写 |
| **Interference** | 干扰观察（不等于失败） |
| **Node** | DAG 节点；对应 `NodeRun` |
| **Oracle Layer** | 预期来源层：REQ / STD / PATTERN |
| **Outbox** | 事件分发的事务型中转表 |
| **Platform Binding** | 一条 AC 到各端 workflow_ref 的映射 |
| **Profile** | 见 Execution Profile |
| **Run** | TestRun，一次执行实例 |
| **seq** | 单 Run 事件严格递增序号 |
| **Skill** | Agent Skills 开放标准封装的能力包（SKILL.md） |
| **Snapshot** | Run 启动时固化的环境/依赖/数据状态 |
| **Triage** | 失败归因流程 |
| **Workflow** | WorkflowDefinition，已批准的 DAG |

### B.1 数据隔离与全局表（batch-276 M-6）

**一条规则**：Run 子表**不存** `project_id`，一律继承 `run.project_id`；跨表查询必须 join `test_runs` 并带 `project_id` 过滤。下表"归属"列是唯一口径。

| 表 | project 归属 | 查询约束 |
|----|-------------|---------|
| `requirement_contracts / test_scenarios / workflow_definitions / test_runs / execution_profiles / environments / defects / project_adapters` | 自带 `project_id`（直接过滤） | 相关索引首列必须是 `project_id` |
| `acceptance_criteria` | 继承 `requirement_contracts.project_id` | join `requirement_contracts` |
| `test_cases` | 继承 `test_scenarios.project_id`（无 `project_id` 列） | join `test_scenarios` |
| `node_runs / step_attempts / assertion_results / run_events / event_outbox / run_artifacts / interference_observations / triage_cases / triage_hypotheses / regression_requests` | 继承 `test_runs.project_id` | join `test_runs`（`regression_requests` 经 `defects` 或 `test_runs.retest_of`） |
| `agent_executions` | **全局表**：`project_id` nullable，按调用方项目写入但不强制隔离 | 可选按 `project_id` 过滤；跨项目审计仅 TL / 管理员 |
| `learning_candidates / bug_patterns / node_capability_manifests` | **全局表**：无 `project_id`，用 `applicable_scope_json` / `node_id` 表达作用域 | 只按 scope 过滤；跨项目写入必须人审 |
| `noise_suppression_rules` | 半全局：`scope = project` 时 `scope_ref` 即 project_id | 先按 project 精确匹配，再回落全局规则 |
| `lanhu_evidence_job / page / asset / ocr_block`（现有） | 自带 `project_id`（不并入本规格表） | 见 §4.12 证据边界 |

**禁止**：Run 子表加 `project_id` 冗余列（会与 `run.project_id` 漂移）；用 `agent_executions.project_id = NULL` 冒充"全项目可见"。

## 附录 C：Durability 分 DB 兼容表

> batch-276 D-1 补充：seq 分配（§8.3.1）与迁移 / 锁 / JSON 的方言差异集中在本表；其余章节不写方言分支。

| 能力 | SQLite（dev / test） | PostgreSQL（prod） | 代码约束 |
|------|---------------------|-------------------|---------|
| 主键 | 整数 PK / UUID 以 CHAR(36) 存 | `uuid` 类型 | 业务模型统一 UUID v4；Alembic 按方言分支 |
| 时间 | `DATETIME`，**naive UTC** | `timestamptz` | 全链路 UTC；与 `task_queue.utcnow()` 口径一致 |
| JSON | `TEXT` 存 JSON 字符串 | `jsonb` | SQLAlchemy `JSON` 类型 + Pydantic `schema_version` |
| 行锁 | 无（单写者） | `SELECT ... FOR UPDATE` | 仓储层封装，业务代码不写方言分支 |
| 咨询锁 | 无 → 事务串行 | `pg_try_advisory_xact_lock(hashtextextended(k, 0))` | 仅 `resource_lock` 与 seq 分配使用 |
| 队列认领 | 条件 UPDATE + rowcount | 同左（或 `FOR UPDATE SKIP LOCKED`） | 复用 `app/core/task_queue.py::atomic_claim` |
| 单 Run 事件 seq | 计数器行 UPDATE（单写者串行） | advisory lock + 计数器行 `UPDATE ... RETURNING` | 唯一索引 `(run_id, seq)` 兜底（§8.3.1） |
| 迁移 | `alembic upgrade head` | 同左 | CI 双端都跑：SQLite 每次 PR，PG 每日 `pr-check` |
| 降级 | ALTER 能力受限 | 完整 | DROP / ALTER 必须带存在性守卫（§0 P0-2） |

**结论**：V1 不依赖 PG-only 能力（排他约束、`LISTEN/NOTIFY` 作为唯一事件通道等）；方言差异只允许收敛在 `repository` / `resource_lock` / `seq` 三处。

---

## 使用说明

- 本规格是 **目标模型 + 契约 + 落地任务**；**已完成 TA-001 代码审计**（[`docs/aiqe/baseline.md`](../aiqe/baseline.md)，batch-278），与现状冲突处以基线为准（C-01..C-10）。
- 实施前必须读 baseline 的**映射矩阵**（25 表）、**冲突登记**与**迁移批次**；D-278-1..3 已确认并写入 v1.3（ID 类型 / `version_task_run` 兼容 / 前端目录）。
- 如果现有稳定代码与本文建议冲突，**以现有稳定代码为准**；但必须保留本文的**事实源边界、执行证据、噪音归因、安全约束**。
- 逐个 GitHub Issue 实施：**先开分支 → 读 Issue 与本规格相关章节 → 更新 ADR/schema → 编码 → 单测 + 集成 + 负向 → Driver Contract Tests → PR → CI + 负责人验收**。
- 禁止一个 PR 同时引入**多套 Run 或 Agent Runtime**。

---

> 本文件 **status: active / v1.3-baseline-aligned**；任何修改走 Agent Team 门禁（批次与里程碑见 [`14-aiqe-dev-schedule-and-dogfood-plan.md`](14-aiqe-dev-schedule-and-dogfood-plan.md)）。
> 本文 + `docs/aiqe/baseline.md` 共同构成 CamelTv AIQE 的**权威工程规格**。

