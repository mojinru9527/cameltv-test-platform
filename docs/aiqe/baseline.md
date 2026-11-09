---
title: "CamelTv AIQE 代码基线审计（TA-001）"
owner: "qa-team"
created: "2026-11-09"
last_reviewed: "2026-11-09"
status: "active"
version: "v1.1-decisions-confirmed"
tags: ["platform-refactor", "aiqe", "baseline", "code-audit"]
related:
  - "docs/platform-refactor/13-ai-quality-agent-merged-spec.md"
  - "docs/platform-refactor/14-aiqe-dev-schedule-and-dogfood-plan.md"
  - "work-logs/batch-278-aiqe-ta-001-baseline-audit-prd-lite.md"
---

# CamelTv AIQE 代码基线审计（TA-001）

> **用途**：在 M1 开工前，把 13 号规格的 25 张目标表 / 8 个服务接入点 / 30 个 REST 端点 / 前端目录 / Driver 能力，与仓库**真实代码**逐项对账，给出可执行的迁移策略与工作量预估。
> **口径**：本文件是 **TA-001 的唯一事实源**；与 13 号冲突时，**以本文件的现状事实为准**，规格按本文件收窄。
> **证据**：所有数字来自 AST 解析 `app/models/`、导入 `app.main` 导出 OpenAPI、以及 `app/services/` / `frontend/src/` 目录统计（命令见 §14）。
> **审计基线**：`origin/main @ 0af75a821`（batch-276 合入后）。

---

## 0. 结论摘要（TL;DR）

| # | 结论 | 对 13 号的影响 |
|---|------|---------------|
| 1 | **ID 类型冲突**：73 张现有表中 **72 张是 `INTEGER` 自增主键**，仅 `ai_task` 是 `str`；13 号要求"所有 ID UUID v4" | 规格需收窄：**新建实体 UUID；指向现有表的外键一律 BIGINT**（§3 C-01） |
| 2 | **`project_id` 是 INT**：50 张表带 `project_id`，全部 `Mapped[int]` | 新表 `project_id` 用 BIGINT；附录 B.1 的隔离规则不变，仅类型对齐 |
| 3 | **"43 张真实表"口径有误**：`app/models/` 是 **43 个文件 / 73 张表** | 13 号 §0、14 号 §4.1 的"43 张"应改为"43 文件 / 73 表" |
| 4 | **时间是 naive UTC、JSON 存 TEXT**：现有模型全部 `Mapped[datetime]` + `*_json: Mapped[str]` | 新表跟随现有约定；附录 C 的双端兼容表维持不变 |
| 5 | **执行链不是规格假设的三段式**：版本任务 `start_run` 是**同步 for 循环**，没有 ExecutionJob / Node / Event | Run/Node/Event 是**新增事实层**，不是现有链改名（§10） |
| 6 | **节点协议已存在且可用**：`execution_job_service` + `scripts/node/cameltv_node`（30s 心跳 / 300s 租约 / sha256 证据对账 / `api`+`web` 执行） | TA-009/010/013 直接复用，**不需要从零写节点** |
| 7 | **§18.5 的 8 个接入点全部存在**；服务文件实为 **71 个顶层 / 123 个递归**（规格写"60+"） | 接入点结论成立，数字修正 |
| 8 | **REST 复用率低**：30 个规格端点中，**1 个可直接复用 + 1 个语义接近**，其余 28 个需新建；`/runs`、`/triage`、`/workflows`、`/learning-candidates` 完全缺失 | §15.2 是净新增工作量，排期需含 28 个端点 |
| 9 | **前端目录结构要改口径**：规格建议 `features/`，实际是 `pages/<domain>/`（19 域 / 153 页面组件 / 30 路由） | §18.2 改为在 `pages/runs`、`pages/triage` 落地 |
| 10 | **P0-4/P0-5 现状确认**：`ai_gateway/`（8 文件）+ 3 个 ai_* model 仍在；`playwright_executor.py` 仍在控制面 | batch-277 的删除/剥离清单准确、可执行 |

**一句话**：13 号的**领域模型和治理规则可用**，但**类型系统（ID/时间/JSON）与现有代码不一致**，且**执行链假设比现实乐观**；M1 可以开工，前提是先接受 §3 的 5 条收窄决策。

---

## 1. 审计范围与方法

| 维度 | 范围 | 方法 |
|------|------|------|
| 数据模型 | `test-platform-v2/backend/app/models/*.py`（43 文件） | Python AST 解析 class / `__tablename__` / `Mapped[...]` / `mapped_column`，**不导入 ORM**（避免副作用） |
| 服务层 | `app/services/**/*.py`（123 文件） | 目录统计 + 对 13 号 §18.5 的 8 个接入点逐个 `Test-Path` + 关键函数 grep |
| 路由层 | `app/api/v1/*.py`（45 文件） | 导入 `app.main` → `app.openapi()` 导出真实 path/method（265 paths / 323 operations） |
| 前端 | `frontend/src/pages/**`、`router/index.tsx` | 目录统计 + 路由表提取（30 条路由） |
| Driver / Node | `scripts/node/cameltv_node/`、`app/services/playwright_executor.py`、`openapi_import_service.py` | 读实现头部 + 关键常量（心跳/租约/证据） |
| 迁移 | `alembic/versions/*.py` | 文件计数（118 revisions）+ 现状约定抽查 |

**不做**：不跑全量测试、不改代码、不动数据库；行号/计数为审计时点快照。

---

## 2. 现状总览（数字）

| 指标 | 实测 | 规格/排期原口径 | 差异 |
|------|------|----------------|------|
| 模型文件 | **43** | 43 | ✅ 一致 |
| 真实表（ORM class） | **73** | "43 张真实表" | ❌ 口径错（文件 vs 表） |
| 主键类型 | **INTEGER ×72 / str ×1** | 全部 UUID v4 | ❌ 需收窄 |
| 带 `project_id` 的表 | **50（全 INT）** | — | 需类型对齐 |
| Alembic revisions | **118** | — | 单 head 需 CI 守卫（TA-001.5） |
| 服务文件 | **71 顶层 / 123 递归** | "60+" | ⚠️ 数量修正 |
| API 模块 | **45 文件 / 265 paths / 323 operations** | "20+ endpoint" | 现状远多于规格清单 |
| 前端页面 | **19 域 / 153 页面组件 / 30 路由** | §18.2 建议 6 个 `features/` 目录 | 结构口径需改 |
| 默认数据库 | `sqlite:///./data/platform.db` | SQLite 开发 / PG 生产 | ✅ 一致 |
| 节点心跳 / 租约 | **30s / 300s** | 规格无具体值 | 直接复用 |

---

## 3. 关键冲突与处置建议

### C-01 主键类型：INT 现状 vs UUID 规格 —— **P0**

- **事实**：72/73 表 `id: Mapped[int]`（`autoincrement`），仅 `ai_task.id: Mapped[str]`。
- **影响**：`test_runs.run_id`(UUID) → `node_runs`(UUID) 没问题；但 `test_runs.environment_id` / `defects.linked_case_id` / `node_runs.execution_job_id` / `run_artifacts` 的 project 过滤全部要落到 INT 上。若照规格全 UUID，会产生 UUID↔INT 隐式转换或双列。
- **建议（需确认）**：
  1. **新建实体一律 UUID v4**（test_runs / node_runs / step_attempts / assertion_results / run_events / run_artifacts / triage_* / regression_requests / agent_executions / learning_candidates / bug_patterns / noise_suppression_rules / execution_profiles / requirement_contracts / acceptance_criteria / test_scenarios / workflow_definitions / project_adapters / node_capability_manifests）；
  2. **指向现有表的外键用 BIGINT**：`project_id`、`environment_id`、`execution_job_id`、`defect_id`、`test_case_id`、`legacy_*_id`；
  3. 新表引用新表用 UUID（`run_id`、`node_run_id`、`contract_id`、`scenario_id`、`triage_case_id`、`learning_candidate_id`）。
- **落地**：13 号 §4 的"所有 ID 使用 UUID v4"改为"新建实体 UUID v4；跨接现有表的外键用 BIGINT，命名显式（`*_legacy_id` 仅用于迁移期）"。

### C-02 时间：naive UTC vs timestamptz —— **P1**

- **事实**：现有 `Mapped[datetime]` 全为 naive（`task_queue.utcnow()` 明确按 naive UTC 处理）；SQLite 无时区。
- **建议**：新表沿用 **naive UTC**；PG 侧用 `timestamptz` 时由 Alembic 方言分支或统一 `DateTime(timezone=True)` 但业务层只读写 UTC。写入/比较一律 `datetime.now(UTC).replace(tzinfo=None)`（与现有 `task_queue.utcnow` 一致）。

### C-03 JSON：TEXT 现状 vs JSONB 规格 —— **P1**

- **事实**：`execution_jobs.payload_json`、`defect` 关联字段等全部 `Mapped[str]`（TEXT 存 JSON 字符串），无 `sa.JSON`。
- **建议**：新表用 `sa.JSON`（SQLite 存 TEXT、PG 存 jsonb），**不为旧表做 JSON 类型迁移**；读写边界用 Pydantic 校验 + `schema_version`（TA-004.2）。

### C-04 执行链：同步循环 vs 分布式 Run —— **P0**

- **事实**：`version_task_service.start_run()` 在 API 请求内**同步 for 循环**跑完所有 adopted 条目（`version_task_exec_service.execute_item`），只写 `version_task_run` 的 `progress/total/passed/failed/skipped/blocked/evidence/failures`；**没有** ExecutionJob、没有节点、没有事件、没有步骤级 attempt；取消只能整任务置 `cancelled`，不能中断执行中的条目。
- **建议**：AIQE 的 Run/Node/Step/Event 作为**新增事实层**，把版本任务作为 `source_type=version_task` 的适配来源；M1 只做"新建 Run 与事件落库"，**不重写**版本任务执行器；M2 起版本任务切到新的 DAG 调度（保留旧路径灰度）。

### C-05 模型命名与系统表 —— **P2**

- **事实**：命名三类并存：`sys_*`（用户/角色/项目/审计）、单数业务表（`defect`、`environment`、`test_case`）、复数（`execution_jobs`、`ai_agents`）。规格目标表为复数 snake_case。
- **建议**：**新表统一复数 snake_case**；旧表不改名（改名会牵动 118 个迁移与全部 ORM 引用）。

### C-06 ai_* 残留与 P0-5 删除清单 —— **P0（batch-277）**

- **事实**：`app/services/ai_gateway/`（8 个 .py）、`app/models/ai_job.py`（表 `ai_agents`）、`ai_shadow_run.py`、`ai_gateway_cache.py`（表 `ai_response_cache`）全部还在。
- **建议**：batch-277 按 §0 P0-5 删除；删除前确认 `ai_task`（独立表，平台内部 AI 任务队列）**不在删除清单**——`ai_job.py` 与 `ai_task.py` 是两张不同表，勿误删。

### C-07 控制面内置浏览器 —— **P0（batch-277）**

- **事实**：`app/services/playwright_executor.py` 用 `subprocess` 调 `npx playwright test`，产物落 `storage/ui-runs`，是 `/uitest` 的执行腿；`cameltv-node` 已能跑 `web` kind。
- **建议**：batch-277 T277-4 把 `/uitest` 执行路径切到 node（`execution_jobs(kind="ui")`），控制面删除 Chromium 依赖；`playwright_executor.py` 降级为只读回放/兼容层。

### C-08 证据模型：两套并存 —— **P1**

- **事实**：`defect_attachment`（缺陷附件）、`ui_test_run.artifact_dir/html_report_path`（目录字符串）、`execution_jobs.evidence_bundle_id`（指向证据包校验）、`lanhu_evidence_asset`（蓝湖资产）四种证据载体并存，**没有统一的 sha256 可寻址 artifact 表**。
- **建议**：新建 `run_artifacts` 作为 Run 证据事实表；`evidence_bundle_service` 的 manifest 校验逻辑复用到 Artifact 上传；`defect_attachment` 保留（缺陷附件不是 Run 证据）。

### C-09 路由命名：现已 27 个业务段 —— **P1**

- **事实**：现有 `/api/v1/*` 有 27 个顶层段（`apitest` 27 ops、`version-tasks` 25、`test-cases` 23、`requirements` 21、`ui-tests` 20…），规格要求新前缀 `/api/v1/aiqe/`。
- **建议**：按 §15.1 用 `/api/v1/aiqe/` 新前缀，**不与现有段混用**；`test-cases/{id}/review` 这类已存在语义的端点，M3 时评估"迁移 vs 包装"，M1 不碰。

### C-10 规格"22 张目标表"口径 —— **P2**

- **事实**：13 号 §4 实际展开 **25 张表**；其中 3 张是"扩展现有模型"（`test_runs`←`version_task_run` 兼容、`environments`←`environment`、`defects`←`defect`），22 张为**净新建**。
- **建议**：口径统一写"**25 张目标表（22 净新建 + 3 扩展）**"，后续文档与 CI 守卫按这个数。

---

## 4. 目标表 → 现有表映射矩阵

| # | 目标表 | 现有同义/相邻表 | 处置 | 类型对齐要点 |
|---|--------|----------------|------|--------------|
| 1 | `requirement_contracts` | `requirement_document`(30) | **新建 + 兼容层** | `source_document_id BIGINT` |
| 2 | `acceptance_criteria` | —（`requirement_document` 无 AC 表） | 新建 | `contract_id UUID` |
| 3 | `test_scenarios` | — | 新建 | `contract_version_id UUID` |
| 4 | `test_cases` | `test_case`(37) + `test_case_version`(7) | **ALTER 扩展** | 保留 `id INT`；`scenario_id UUID` |
| 5 | `workflow_definitions` | —（`test_plan` 不是 DAG） | 新建 | `scenario_id UUID` |
| 6 | `test_runs` | `version_task_run`(13)、`api_execution_task`(22)、`ui_test_run`(20) | **新建 + 旧表兼容** | `environment_id BIGINT`；`legacy_version_task_run_id BIGINT` |
| 7 | `node_runs` | `execution_jobs`(19) | 新建 | `run_id UUID`；`execution_job_id BIGINT` |
| 8 | `step_attempts` | —（`api_execution_task_item` 无步骤级） | 新建 | `node_run_id UUID` |
| 9 | `assertion_results` | `runner_execution_task.assertions`（入参非结果） | 新建 | `step_attempt_id UUID` |
| 10 | `run_events` | — | 新建 | `run_id UUID`；`(run_id, seq)` 唯一 |
| 11 | `event_outbox` | —（队列≠事件） | 新建 | `run_event_id UUID` |
| 12 | `run_artifacts` | `defect_attachment`(9)、`ui_test_run`(20) | 新建 | `run_id UUID`；`linked_evidence_id VARCHAR` |
| 13 | `execution_profiles` | `environment.access_type/execution_mode`（环境级开关） | 新建 | `project_id BIGINT` |
| 14 | `environments` | `environment`(10) + `environment_variable`(6) | **ALTER 扩展** | 保留 `id INT`；+4 字段 |
| 15 | `interference_observations` | — | 新建 | `run_id / node_run_id UUID` |
| 16 | `triage_cases` | — | 新建 | `run_id UUID` |
| 17 | `triage_hypotheses` | — | 新建 | `triage_case_id UUID` |
| 18 | `defects` | `defect`(17) + transition/comment/attachment | **ALTER 扩展** | 保留 `id INT`；`linked_ac_id UUID`、`triage_case_id UUID` |
| 19 | `regression_requests` | `test_plan_case.last_status`（计划内快照） | 新建 | `defect_id BIGINT`、`new_run_id UUID` |
| 20 | `agent_executions` | `ai_task`(12)、`model_usage_ledger`(10) | 新建（双写台账） | `project_id BIGINT` nullable |
| 21 | `learning_candidates` | `reuse_suggestion_event`(7)（决策记录） | 新建 | `source_ref VARCHAR` |
| 22 | `bug_patterns` | `knowledge_entity`(12)（知识图谱） | 新建 | `learning_candidate_id UUID` |
| 23 | `noise_suppression_rules` | — | 新建 | `scope_ref VARCHAR`；自引用 `renewal_of_rule_id UUID` |
| 24 | `project_adapters` | `project`(7)（项目元数据） | 新建 | `project_id BIGINT` |
| 25 | `node_capability_manifests` | `execution_jobs` 节点态（非能力清单） | 新建 | `node_id VARCHAR` |

**合计**：22 净新建 + 3 扩展；目标字段 315 个；迁移脚本预估 **≈ 2090 行**（Alembic revision + 索引 + 回填）。

---

## 5. 逐表对账

> 每节格式：目标字段 → 现有候选（类/文件/列）→ 差异（同名/目标新增/现有独有）→ 迁移策略 → 预估行数。
> "现有独有"列**不删除**：旧表继续服务现有页面，新表只承接 AIQE 语义。

### 4.2 `requirement_contracts`

**目标字段**（13 号 §4.2）：15 个 — `id`、`project_id`、`requirement_id`、`version`、`source_docs_json`、`intent`、`business_rules_json`、`open_questions_json`、`conflicts_json`、`checksum`、`approval_status`、`approved_by`、`approved_at`、`created_at`、`updated_at`

**现有候选**：

- `requirement_document`（RequirementDocument，test-platform-v2/backend/app/models/requirement.py，30 列）：`id`、`project_id`、`creator_id`、`title`、`file_type`、`source_ref`、`source_url`、`content`、`ai_raw`、`status`、`imported_count`、`imported_func_count`、`imported_api_count`、`imported_func_indices`、`imported_api_indices`、`extraction_raw`、`extraction_status`、`extraction_state`、`extraction_meta`、`extraction_progress`、`platform`、`doc_type`、`doc_id`、`version`、`parent_id`、`diff_json`、`diff_status`、`release_bundle_id`、`linked_swagger_id`、`linked_api_endpoint_ids`


**差异**：同名字段 3 / 目标新增 12 / 现有独有 27

- 同名（可直接复用）：`id`、`project_id`、`version`

- 目标新增（需 ALTER 或新表）：`requirement_id`、`source_docs_json`、`intent`、`business_rules_json`、`open_questions_json`、`conflicts_json`、`checksum`、`approval_status`、`approved_by`、`approved_at`、`created_at`、`updated_at`

- 现有独有（保留，不删）：`ai_raw`、`content`、`creator_id`、`diff_json`、`diff_status`、`doc_id`、`doc_type`、`extraction_meta`、`extraction_progress`、`extraction_raw`、`extraction_state`、`extraction_status`、`file_type`、`imported_api_count`、`imported_api_indices`、`imported_count`、`imported_func_count`、`imported_func_indices`、`linked_api_endpoint_ids`、`linked_swagger_id`、`parent_id`、`platform`、`release_bundle_id`、`source_ref`、`source_url`、`status`、`title`

- **迁移策略**：新建 `requirement_contracts`（冻结版本 + checksum）。现有 `requirement_document` 保留为**草稿/导入入口**（兼容层），冻结时把标题/平台/版本/内容哈希写入新表；`requirement_contracts.source_document_id` 用 BIGINT 指向旧表。

- **预估迁移脚本行数**：≈ 95（Alembic revision + 索引 + 回填）


### 4.3 `acceptance_criteria`

**目标字段**（13 号 §4.3）：11 个 — `id`、`contract_id`、`ac_key`、`given_json`、`when_action`、`then_json`、`platforms_json`、`source_refs_json`、`ambiguity`、`derived`、`created_at`

**现有候选**：无同义表（新建）


**差异**：同名字段 0 / 目标新增 11 / 现有独有 0

- 目标新增（需 ALTER 或新表）：`id`、`contract_id`、`ac_key`、`given_json`、`when_action`、`then_json`、`platforms_json`、`source_refs_json`、`ambiguity`、`derived`、`created_at`

- **迁移策略**：新建 `acceptance_criteria`（结构化 AC + derived 标记）。现有 `requirement_document` 无 AC 表，A1 产出直接落新表，`contract_id` UUID + `source_refs_json` 指回文档章节。

- **预估迁移脚本行数**：≈ 80（Alembic revision + 索引 + 回填）


### 4.4 `test_scenarios`

**目标字段**（13 号 §4.4）：12 个 — `id`、`project_id`、`scenario_key`、`title`、`intent`、`contract_version_id`、`risk_level`、`status`、`version`、`created_by`、`created_at`、`updated_at`

**现有候选**：无同义表（新建）


**差异**：同名字段 0 / 目标新增 12 / 现有独有 0

- 目标新增（需 ALTER 或新表）：`id`、`project_id`、`scenario_key`、`title`、`intent`、`contract_version_id`、`risk_level`、`status`、`version`、`created_by`、`created_at`、`updated_at`

- **迁移策略**：新建 `test_scenarios`（契约版本 → 场景）。现有无场景实体，`test_case` 的 `domain/module` 只到分类层，不复用。

- **预估迁移脚本行数**：≈ 85（Alembic revision + 索引 + 回填）


### 4.5 `test_cases`

**目标字段**（13 号 §4.5）：20 个 — `id`、`scenario_id`、`case_key`、`title`、`case_type`、`priority`、`preconditions_json`、`data_plan_json`、`steps_json`、`assertions_json`、`platform_bindings_json`、`dependencies_json`、`cleanup_json`、`automation_level`、`review_status`、`version`、`source_json`、`schema_version`、`created_at`、`updated_at`

**现有候选**：

- `test_case`（TestCase，test-platform-v2/backend/app/models/test_case.py，37 列）：`id`、`project_id`、`case_id`、`title`、`domain`、`module`、`is_deleted`、`case_type`、`priority`、`status`、`tags`、`case_design_method`、`positive_negative`、`test_data_note`、`preconditions`、`steps`、`expected_result`、`api_method`、`api_endpoint`、`api_spec_ref`、`api_headers`、`api_body`、`api_assertions`、`depends_on_ids`、`last_response_json`、`last_run_status`、`dataset_id`、`api_endpoint_id`、`requirement_module_id`、`source`、`source_req_id`、`source_doc_id`、`source_case_index`、`old_id`、`review_status`、`review_comment`、`reviewer_id`

- `test_case_version`（TestCaseVersion，test-platform-v2/backend/app/models/test_case_version.py，7 列）：`id`、`case_id`、`version_number`、`snapshot`、`changed_by`、`changed_fields`、`created_at`


**差异**：同名字段 6 / 目标新增 14 / 现有独有 36

- 同名（可直接复用）：`id`、`title`、`case_type`、`priority`、`review_status`、`created_at`

- 目标新增（需 ALTER 或新表）：`scenario_id`、`case_key`、`preconditions_json`、`data_plan_json`、`steps_json`、`assertions_json`、`platform_bindings_json`、`dependencies_json`、`cleanup_json`、`automation_level`、`version`、`source_json`、`schema_version`、`updated_at`

- 现有独有（保留，不删）：`api_assertions`、`api_body`、`api_endpoint`、`api_endpoint_id`、`api_headers`、`api_method`、`api_spec_ref`、`case_design_method`、`case_id`、`changed_by`、`changed_fields`、`dataset_id`、`depends_on_ids`、`domain`、`expected_result`、`is_deleted`、`last_response_json`、`last_run_status`、`module`、`old_id`、`positive_negative`、`preconditions`、`project_id`、`requirement_module_id`、`review_comment`、`reviewer_id`、`snapshot`、`source`、`source_case_index`、`source_doc_id`、`source_req_id`、`status`、`steps`、`tags`、`test_data_note`、`version_number`

- **迁移策略**：**ALTER 扩展现有 `test_case`**：保留 37 列（`case_id/title/steps/expected_result/api_*` 已覆盖大部分），新增 `scenario_id`(UUID, nullable)、`platform_bindings_json`、`cleanup_json`、`schema_version`、`automation_level`；`project_id` 保持 INT。**语义映射（人工复核）**：`case_id`≈`case_key`、`steps`≈`steps_json`、`preconditions`≈`preconditions_json`、`expected_result`+`api_assertions`≈`assertions_json` 的输入、`version_number`≈`version`。禁止新建平行用例表。

- **预估迁移脚本行数**：≈ 90（Alembic revision + 索引 + 回填）


### 4.6 `workflow_definitions`

**目标字段**（13 号 §4.6）：12 个 — `id`、`project_id`、`scenario_id`、`version`、`graph_json`、`schema_version`、`checksum`、`validation_status`、`approval_status`、`approved_by`、`approved_at`、`created_at`

**现有候选**：无同义表（新建）


**差异**：同名字段 0 / 目标新增 12 / 现有独有 0

- 目标新增（需 ALTER 或新表）：`id`、`project_id`、`scenario_id`、`version`、`graph_json`、`schema_version`、`checksum`、`validation_status`、`approval_status`、`approved_by`、`approved_at`、`created_at`

- **迁移策略**：新建 `workflow_definitions`（graph_json + checksum + approval），无现有实体；与 `TestPlan` 不是同一概念（计划是选例集合，Workflow 是执行 DAG），迁移时不合并。

- **预估迁移脚本行数**：≈ 85（Alembic revision + 索引 + 回填）


### 4.7 `test_runs`

**目标字段**（13 号 §4.7）：20 个 — `id`、`project_id`、`run_key`、`source_type`、`source_id`、`scenario_id`、`workflow_definition_id`、`build_ref`、`commit_sha`、`environment_id`、`execution_profile_id`、`environment_snapshot_json`、`retest_of`、`status`、`outcome`、`trigger_user_id`、`started_at`、`finished_at`、`duration_ms`、`created_at`

**现有候选**：

- `version_task_run`（VersionTaskRun，test-platform-v2/backend/app/models/version_task_run.py，13 列）：`id`、`task_id`、`status`、`progress`、`total`、`passed`、`failed`、`skipped`、`blocked`、`evidence`、`failures`、`started_at`、`finished_at`

- `api_execution_task`（ApiExecutionTask，test-platform-v2/backend/app/models/api_asset.py，22 列）：`id`、`project_id`、`task_id`、`name`、`environment_id`、`service_id`、`status`、`total`、`passed`、`failed`、`skipped`、`trigger_type`、`creator_id`、`started_at`、`finished_at`、`cancel_requested`、`confirm_prod`、`retry_count`、`max_retries`、`locked_at`、`locked_by`、`timeout_seconds`

- `ui_test_run`（UiTestRun，test-platform-v2/backend/app/models/ui_test.py，20 列）：`id`、`job_id`、`status`、`result`、`screenshots`、`video_url`、`trace_id`、`base_url`、`artifact_dir`、`report_json_path`、`html_report_path`、`error_message`、`stdout`、`stderr`、`process_id`、`cancel_requested`、`started_at`、`finished_at`、`locked_at`、`locked_by`


**差异**：同名字段 6 / 目标新增 14 / 现有独有 33

- 同名（可直接复用）：`id`、`project_id`、`environment_id`、`status`、`started_at`、`finished_at`

- 目标新增（需 ALTER 或新表）：`run_key`、`source_type`、`source_id`、`scenario_id`、`workflow_definition_id`、`build_ref`、`commit_sha`、`execution_profile_id`、`environment_snapshot_json`、`retest_of`、`outcome`、`trigger_user_id`、`duration_ms`、`created_at`

- 现有独有（保留，不删）：`artifact_dir`、`base_url`、`blocked`、`cancel_requested`、`confirm_prod`、`creator_id`、`error_message`、`evidence`、`failed`、`failures`、`html_report_path`、`job_id`、`locked_at`、`locked_by`、`max_retries`、`name`、`passed`、`process_id`、`progress`、`report_json_path`、`result`、`retry_count`、`screenshots`、`service_id`、`skipped`、`stderr`、`stdout`、`task_id`、`timeout_seconds`、`total`、`trace_id`、`trigger_type`、`video_url`

- **迁移策略**：**新建 `test_runs`（UUID）作为通用执行事实表**；`version_task_run` 保留并新增 `test_run_id BIGINT` 回填（M1-M2 双写），M2 后旧表只读、V1.1 删表。`api_execution_task` / `ui_test_run` 作为 `source_type=api_task/ui` 的适配来源，不迁数据。**语义映射**：`version_task_run.task_id`→`legacy_task_id`；`status/progress/total/passed/failed` 是**汇总**，与 Run 的 `status × outcome` 不同语义，只做只读展示。

- **预估迁移脚本行数**：≈ 105（Alembic revision + 索引 + 回填）


### 4.8 `node_runs`

**目标字段**（13 号 §4.8）：14 个 — `id`、`run_id`、`node_key`、`driver_key`、`worker_id`、`status`、`input_ref`、`output_ref`、`error_class`、`resource_keys_json`、`execution_job_id`、`started_at`、`finished_at`、`attempt_count`

**现有候选**：

- `execution_jobs`（ExecutionJob，test-platform-v2/backend/app/models/execution_job.py，19 列）：`id`、`project_id`、`kind`、`status`、`case_refs_json`、`payload_json`、`env_ref`、`attempt`、`timeout_seconds`、`node_id`、`claimed_at`、`lease_expires_at`、`heartbeat_at`、`started_at`、`finished_at`、`evidence_bundle_id`、`result_json`、`summary`、`error_message`


**差异**：同名字段 4 / 目标新增 10 / 现有独有 15

- 同名（可直接复用）：`id`、`status`、`started_at`、`finished_at`

- 目标新增（需 ALTER 或新表）：`run_id`、`node_key`、`driver_key`、`worker_id`、`input_ref`、`output_ref`、`error_class`、`resource_keys_json`、`execution_job_id`、`attempt_count`

- 现有独有（保留，不删）：`attempt`、`case_refs_json`、`claimed_at`、`env_ref`、`error_message`、`evidence_bundle_id`、`heartbeat_at`、`kind`、`lease_expires_at`、`node_id`、`payload_json`、`project_id`、`result_json`、`summary`、`timeout_seconds`

- **迁移策略**：新建 `node_runs`；`execution_jobs` 保持派发工作单元语义，`node_runs.execution_job_id` 用 BIGINT 1:1 绑定（未派发为 NULL）。**语义映射**：`execution_jobs.status`→`node_runs.status` 的派发侧子集；`attempt`≈`attempt_count`；`evidence_bundle_id`→`run_artifacts` 聚合。不把 `execution_jobs` 改造成节点事实表。

- **预估迁移脚本行数**：≈ 95（Alembic revision + 索引 + 回填）


### 4.9 `step_attempts`

**目标字段**（13 号 §4.9）：11 个 — `id`、`node_run_id`、`step_key`、`attempt_no`、`status`、`started_at`、`finished_at`、`input_summary_json`、`output_summary_json`、`error_json`、`external_execution_ref`

**现有候选**：无同义表（新建）


**差异**：同名字段 0 / 目标新增 11 / 现有独有 0

- 目标新增（需 ALTER 或新表）：`id`、`node_run_id`、`step_key`、`attempt_no`、`status`、`started_at`、`finished_at`、`input_summary_json`、`output_summary_json`、`error_json`、`external_execution_ref`

- **迁移策略**：新建 `step_attempts`（Attempt 永久保留）。现有 `api_execution_task_item` / `ui_test_run` 只有汇总，无步骤级记录，不复用。

- **预估迁移脚本行数**：≈ 80（Alembic revision + 索引 + 回填）


### 4.10 `assertion_results`

**目标字段**（13 号 §4.10）：11 个 — `id`、`step_attempt_id`、`assertion_key`、`assertion_type`、`rule_id`、`status`、`expected_json`、`actual_json`、`diff_json`、`evidence_refs_json`、`evaluated_by`

**现有候选**：

- `runner_execution_task`（RunnerExecutionTask，test-platform-v2/backend/app/models/runner_execution.py，14 列）：`id`、`project_id`、`environment_id`、`task_id`、`runner_key`、`request`、`assertions`、`status`、`result`、`error_message`、`locked_at`、`locked_by`、`claimed_at`、`finished_at`


**差异**：同名字段 2 / 目标新增 9 / 现有独有 12

- 同名（可直接复用）：`id`、`status`

- 目标新增（需 ALTER 或新表）：`step_attempt_id`、`assertion_key`、`assertion_type`、`rule_id`、`expected_json`、`actual_json`、`diff_json`、`evidence_refs_json`、`evaluated_by`

- 现有独有（保留，不删）：`assertions`、`claimed_at`、`environment_id`、`error_message`、`finished_at`、`locked_at`、`locked_by`、`project_id`、`request`、`result`、`runner_key`、`task_id`

- **迁移策略**：新建 `assertion_results`；现有 `runner_execution_task.assertions` 是任务入参 JSON，不是结果表，不复用。

- **预估迁移脚本行数**：≈ 80（Alembic revision + 索引 + 回填）


### 4.11 `run_events`

**目标字段**（13 号 §4.11）：11 个 — `id`、`run_id`、`seq`、`node_run_id`、`step_attempt_id`、`event_type`、`occurred_at`、`producer`、`correlation_id`、`payload_json`、`producer_event_id`

**现有候选**：无同义表（新建）


**差异**：同名字段 0 / 目标新增 11 / 现有独有 0

- 目标新增（需 ALTER 或新表）：`id`、`run_id`、`seq`、`node_run_id`、`step_attempt_id`、`event_type`、`occurred_at`、`producer`、`correlation_id`、`payload_json`、`producer_event_id`

- **迁移策略**：新建 `run_events`（append-only + `(run_id, seq)` 唯一索引）。现有系统无事件流：`version_task_run` 只有汇总计数，UI/API 任务只有日志字符串。

- **预估迁移脚本行数**：≈ 80（Alembic revision + 索引 + 回填）


### 4.11 `event_outbox`

**目标字段**（13 号 §4.11）：5 个 — `id`、`run_event_id`、`dispatched_at`、`retry_count`、`last_error`

**现有候选**：无同义表（新建）


**差异**：同名字段 0 / 目标新增 5 / 现有独有 0

- 目标新增（需 ALTER 或新表）：`id`、`run_event_id`、`dispatched_at`、`retry_count`、`last_error`

- **迁移策略**：新建 `event_outbox`（同事务落库 + dispatcher 推送）。现有 `ai_task`/`plan_execution_job` 是任务队列语义，不是事件分发，不复用。

- **预估迁移脚本行数**：≈ 50（Alembic revision + 索引 + 回填）


### 4.12 `run_artifacts`

**目标字段**（13 号 §4.12）：14 个 — `id`、`run_id`、`node_run_id`、`step_attempt_id`、`artifact_type`、`storage_uri`、`sha256`、`size_bytes`、`mime_type`、`redaction_status`、`metadata_json`、`linked_evidence_type`、`linked_evidence_id`、`created_at`

**现有候选**：

- `defect_attachment`（DefectAttachment，test-platform-v2/backend/app/models/defect.py，9 列）：`id`、`defect_id`、`filename`、`stored_path`、`file_size`、`mime_type`、`uploader_id`、`uploader_name`、`created_at`

- `ui_test_run`（UiTestRun，test-platform-v2/backend/app/models/ui_test.py，20 列）：`id`、`job_id`、`status`、`result`、`screenshots`、`video_url`、`trace_id`、`base_url`、`artifact_dir`、`report_json_path`、`html_report_path`、`error_message`、`stdout`、`stderr`、`process_id`、`cancel_requested`、`started_at`、`finished_at`、`locked_at`、`locked_by`


**差异**：同名字段 3 / 目标新增 11 / 现有独有 25

- 同名（可直接复用）：`id`、`mime_type`、`created_at`

- 目标新增（需 ALTER 或新表）：`run_id`、`node_run_id`、`step_attempt_id`、`artifact_type`、`storage_uri`、`sha256`、`size_bytes`、`redaction_status`、`metadata_json`、`linked_evidence_type`、`linked_evidence_id`

- 现有独有（保留，不删）：`artifact_dir`、`base_url`、`cancel_requested`、`defect_id`、`error_message`、`file_size`、`filename`、`finished_at`、`html_report_path`、`job_id`、`locked_at`、`locked_by`、`process_id`、`report_json_path`、`result`、`screenshots`、`started_at`、`status`、`stderr`、`stdout`、`stored_path`、`trace_id`、`uploader_id`、`uploader_name`、`video_url`

- **迁移策略**：新建 `run_artifacts`（sha256 + storage_uri + redaction）。现有 `defect_attachment`（缺陷附件）与 `ui_test_run.artifact_dir`（目录字符串）都不是可寻址证据表，不复用；跨源引用用 `linked_evidence_type/id`。

- **预估迁移脚本行数**：≈ 95（Alembic revision + 索引 + 回填）


### 4.13 `execution_profiles`

**目标字段**（13 号 §4.13）：11 个 — `id`、`project_id`、`name`、`purpose`、`config_json`、`version`、`checksum`、`approval_status`、`owner_id`、`expires_at`、`created_at`

**现有候选**：无同义表（新建）


**差异**：同名字段 0 / 目标新增 11 / 现有独有 0

- 目标新增（需 ALTER 或新表）：`id`、`project_id`、`name`、`purpose`、`config_json`、`version`、`checksum`、`approval_status`、`owner_id`、`expires_at`、`created_at`

- **迁移策略**：新建 `execution_profiles`（三档 profile + checksum）。现有 `environment.access_type/execution_mode` 是环境级开关，不能表达 Run 级隔离策略，不复用。

- **预估迁移脚本行数**：≈ 80（Alembic revision + 索引 + 回填）


### 4.14 `environments`

**目标字段**（13 号 §4.14）：4 个 — `base_urls_json`、`data_sources_json`、`build_check_endpoint`、`allowed_actions`

**现有候选**：

- `environment`（Environment，test-platform-v2/backend/app/models/environment.py，10 列）：`id`、`project_id`、`name`、`env_type`、`base_url`、`description`、`is_production`、`access_type`、`execution_mode`、`runner_key`

- `environment_variable`（EnvironmentVariable，test-platform-v2/backend/app/models/environment.py，6 列）：`id`、`environment_id`、`key`、`value`、`encrypted`、`description`


**差异**：同名字段 0 / 目标新增 4 / 现有独有 14

- 目标新增（需 ALTER 或新表）：`base_urls_json`、`data_sources_json`、`build_check_endpoint`、`allowed_actions`

- 现有独有（保留，不删）：`access_type`、`base_url`、`description`、`encrypted`、`env_type`、`environment_id`、`execution_mode`、`id`、`is_production`、`key`、`name`、`project_id`、`runner_key`、`value`

- **迁移策略**：**ALTER 扩展现有 `environment`**（10 列 → 14 列）：新增 `base_urls_json`、`data_sources_json`、`build_check_endpoint`、`allowed_actions`；`environment_variable` 保留用于密钥 slot。**语义映射**：现有 `base_url` 作为 `base_urls_json.api` 的初始值；`access_type/execution_mode` 保留，不映射到 `allowed_actions`（后者是 AIQE 写权限，语义不同）。

- **预估迁移脚本行数**：≈ 40（Alembic revision + 索引 + 回填）


### 4.15 `interference_observations`

**目标字段**（13 号 §4.15）：15 个 — `id`、`run_id`、`node_run_id`、`step_attempt_id`、`category`、`signal_type`、`signal_payload_json`、`evidence_refs_json`、`observed_at`、`correlation_id`、`source`、`is_controlled`、`control_action`、`control_result`、`created_by`

**现有候选**：无同义表（新建）


**差异**：同名字段 0 / 目标新增 15 / 现有独有 0

- 目标新增（需 ALTER 或新表）：`id`、`run_id`、`node_run_id`、`step_attempt_id`、`category`、`signal_type`、`signal_payload_json`、`evidence_refs_json`、`observed_at`、`correlation_id`、`source`、`is_controlled`、`control_action`、`control_result`、`created_by`

- **迁移策略**：新建 `interference_observations`。现有无干扰实体；`quality_gate_config` 是门禁配置，不复用。

- **预估迁移脚本行数**：≈ 100（Alembic revision + 索引 + 回填）


### 4.16 `triage_cases`

**目标字段**（13 号 §4.16）：10 个 — `id`、`run_id`、`primary_node_run_id`、`status`、`primary_classification`、`product_scope`、`evidence_completeness`、`created_at`、`resolved_at`、`resolved_by`

**现有候选**：无同义表（新建）


**差异**：同名字段 0 / 目标新增 10 / 现有独有 0

- 目标新增（需 ALTER 或新表）：`id`、`run_id`、`primary_node_run_id`、`status`、`primary_classification`、`product_scope`、`evidence_completeness`、`created_at`、`resolved_at`、`resolved_by`

- **迁移策略**：新建 `triage_cases`。现有缺陷/执行表无归因实体（`defect.status` 只是流转），不复用。

- **预估迁移脚本行数**：≈ 75（Alembic revision + 索引 + 回填）


### 4.16 `triage_hypotheses`

**目标字段**（13 号 §4.16）：13 个 — `id`、`triage_case_id`、`hypothesis_key`、`classification`、`explanation`、`supporting_evidence_json`、`contradicting_evidence_json`、`missing_evidence_json`、`proposed_experiment_json`、`confidence_calibration_version`、`rank`、`verification_status`、`verification_run_id`

**现有候选**：无同义表（新建）


**差异**：同名字段 0 / 目标新增 13 / 现有独有 0

- 目标新增（需 ALTER 或新表）：`id`、`triage_case_id`、`hypothesis_key`、`classification`、`explanation`、`supporting_evidence_json`、`contradicting_evidence_json`、`missing_evidence_json`、`proposed_experiment_json`、`confidence_calibration_version`、`rank`、`verification_status`、`verification_run_id`

- **迁移策略**：新建 `triage_hypotheses`（一失败多假设）。

- **预估迁移脚本行数**：≈ 90（Alembic revision + 索引 + 回填）


### 4.17 `defects`

**目标字段**（13 号 §4.17）：19 个 — `id`、`project_id`、`title`、`severity`、`status`、`assignee`、`creator`、`linked_case_id`、`linked_execution_id`、`linked_ac_id`、`triage_case_id`、`steps_to_reproduce_json`、`expected`、`actual`、`environment_snapshot_json`、`fixed_commit_sha`、`external_id`、`created_at`、`updated_at`

**现有候选**：

- `defect`（Defect，test-platform-v2/backend/app/models/defect.py，17 列）：`id`、`project_id`、`defect_id`、`title`、`description`、`severity`、`status`、`case_id`、`execution_id`、`aitde_run_id`、`assignee_id`、`external_id`、`external_url`、`creator_id`、`resolved_at`、`created_at`、`updated_at`

- `defect_transition`（DefectTransition，test-platform-v2/backend/app/models/defect.py，8 列）：`id`、`defect_id`、`from_status`、`to_status`、`comment`、`operator_id`、`operator_name`、`created_at`

- `defect_comment`（DefectComment，test-platform-v2/backend/app/models/defect.py，6 列）：`id`、`defect_id`、`content`、`author_id`、`author_name`、`created_at`

- `defect_attachment`（DefectAttachment，test-platform-v2/backend/app/models/defect.py，9 列）：`id`、`defect_id`、`filename`、`stored_path`、`file_size`、`mime_type`、`uploader_id`、`uploader_name`、`created_at`


**差异**：同名字段 8 / 目标新增 11 / 现有独有 23

- 同名（可直接复用）：`id`、`project_id`、`title`、`severity`、`status`、`external_id`、`created_at`、`updated_at`

- 目标新增（需 ALTER 或新表）：`assignee`、`creator`、`linked_case_id`、`linked_execution_id`、`linked_ac_id`、`triage_case_id`、`steps_to_reproduce_json`、`expected`、`actual`、`environment_snapshot_json`、`fixed_commit_sha`

- 现有独有（保留，不删）：`aitde_run_id`、`assignee_id`、`author_id`、`author_name`、`case_id`、`comment`、`content`、`creator_id`、`defect_id`、`description`、`execution_id`、`external_url`、`file_size`、`filename`、`from_status`、`mime_type`、`operator_id`、`operator_name`、`resolved_at`、`stored_path`、`to_status`、`uploader_id`、`uploader_name`

- **迁移策略**：**ALTER 扩展现有 `defect`**（17 列）：新增 `linked_ac_id`(UUID)、`triage_case_id`(UUID)、`steps_to_reproduce_json`、`environment_snapshot_json`、`fixed_commit_sha`；保留 `defect_transition/comment/attachment` 三张辅助表继续用。**语义映射**：`case_id`≈`linked_case_id`、`execution_id`≈`linked_execution_id`（执行模型换成 `test_runs` 后需新增 UUID 列）、`aitde_run_id` 随 AITDE 退役废弃。

- **预估迁移脚本行数**：≈ 75（Alembic revision + 索引 + 回填）


### 4.18 `regression_requests`

**目标字段**（13 号 §4.18）：12 个 — `id`、`defect_id`、`source_run_id`、`fixed_commit_sha`、`selection_mode`、`selected_case_ids_json`、`status`、`new_run_id`、`requested_by`、`approved_by`、`created_at`、`completed_at`

**现有候选**：无同义表（新建）


**差异**：同名字段 0 / 目标新增 12 / 现有独有 0

- 目标新增（需 ALTER 或新表）：`id`、`defect_id`、`source_run_id`、`fixed_commit_sha`、`selection_mode`、`selected_case_ids_json`、`status`、`new_run_id`、`requested_by`、`approved_by`、`created_at`、`completed_at`

- **迁移策略**：新建 `regression_requests`。现有 `test_plan_case.last_status` 只是计划内快照，无法承载“回归请求 + 新 Run 关联”，不复用。

- **预估迁移脚本行数**：≈ 85（Alembic revision + 索引 + 回填）


### 4.19 `agent_executions`

**目标字段**（13 号 §4.19）：17 个 — `id`、`project_id`、`agent_key`、`agent_version`、`actor_id`、`task_type`、`provider`、`model`、`prompt_version`、`input_ref`、`output_ref`、`tool_calls_json`、`token_usage_json`、`status`、`error_json`、`started_at`、`finished_at`

**现有候选**：

- `ai_task`（AiTask，test-platform-v2/backend/app/models/ai_task.py，12 列）：`id`、`task_type`、`project_id`、`document_id`、`status`、`progress`、`result_json`、`error`、`locked_at`、`locked_by`、`started_at`、`finished_at`

- `model_usage_ledger`（ModelUsageLedger，test-platform-v2/backend/app/models/model_usage.py，10 列）：`id`、`project_id`、`mission_id`、`operation_type`、`model_ref`、`input_units`、`output_units`、`cost_amount`、`latency_ms`、`created_at`


**差异**：同名字段 6 / 目标新增 11 / 现有独有 14

- 同名（可直接复用）：`id`、`project_id`、`task_type`、`status`、`started_at`、`finished_at`

- 目标新增（需 ALTER 或新表）：`agent_key`、`agent_version`、`actor_id`、`provider`、`model`、`prompt_version`、`input_ref`、`output_ref`、`tool_calls_json`、`token_usage_json`、`error_json`

- 现有独有（保留，不删）：`cost_amount`、`created_at`、`document_id`、`error`、`input_units`、`latency_ms`、`locked_at`、`locked_by`、`mission_id`、`model_ref`、`operation_type`、`output_units`、`progress`、`result_json`

- **迁移策略**：新建 `agent_executions`（每次 Agent 调用一行）。`ai_task` 保留为平台内部异步任务队列（不做删除），`model_usage_ledger` 保留为成本台账；两者与 Agent 审计**双写**，不合并。

- **预估迁移脚本行数**：≈ 110（Alembic revision + 索引 + 回填）


### 4.19 `learning_candidates`

**目标字段**（13 号 §4.19）：13 个 — `id`、`source_type`、`source_ref`、`candidate_rule_json`、`applicable_scope_json`、`counter_examples_json`、`benchmark_result_json`、`status`、`approved_by`、`version`、`effective_from`、`expires_at`、`created_at`

**现有候选**：

- `reuse_suggestion_event`（ReuseSuggestionEvent，test-platform-v2/backend/app/models/reuse_suggestion.py，7 列）：`id`、`project_id`、`task_id`、`suggestion_ref`、`title`、`decision`、`decided_by`

- `version_knowledge_record`（VersionKnowledgeRecord，test-platform-v2/backend/app/models/version_knowledge.py，11 列）：`id`、`project_id`、`task_id`、`version`、`title`、`summary`、`coverage`、`verdict`、`risk`、`plan_summary`、`defect_count`


**差异**：同名字段 2 / 目标新增 11 / 现有独有 12

- 同名（可直接复用）：`id`、`version`

- 目标新增（需 ALTER 或新表）：`source_type`、`source_ref`、`candidate_rule_json`、`applicable_scope_json`、`counter_examples_json`、`benchmark_result_json`、`status`、`approved_by`、`effective_from`、`expires_at`、`created_at`

- 现有独有（保留，不删）：`coverage`、`decided_by`、`decision`、`defect_count`、`plan_summary`、`project_id`、`risk`、`suggestion_ref`、`summary`、`task_id`、`title`、`verdict`

- **迁移策略**：新建 `learning_candidates`。现有 `reuse_suggestion_event` 只记“复用建议决策”，不是候选规则生命周期，不复用。

- **预估迁移脚本行数**：≈ 90（Alembic revision + 索引 + 回填）


### 4.19 `bug_patterns`

**目标字段**（13 号 §4.19）：9 个 — `id`、`pattern_key`、`detection_point`、`trigger_signature`、`test_oracle`、`applicable_scope_json`、`learning_candidate_id`、`version`、`status`

**现有候选**：

- `knowledge_entity`（KnowledgeEntity，test-platform-v2/backend/app/models/knowledge.py，12 列）：`id`、`project_id`、`entity_type`、`entity_key`、`name`、`description`、`source_id`、`business_ref_type`、`business_ref_id`、`confidence`、`review_status`、`metadata_json`

- `version_knowledge_record`（VersionKnowledgeRecord，test-platform-v2/backend/app/models/version_knowledge.py，11 列）：`id`、`project_id`、`task_id`、`version`、`title`、`summary`、`coverage`、`verdict`、`risk`、`plan_summary`、`defect_count`


**差异**：同名字段 2 / 目标新增 7 / 现有独有 19

- 同名（可直接复用）：`id`、`version`

- 目标新增（需 ALTER 或新表）：`pattern_key`、`detection_point`、`trigger_signature`、`test_oracle`、`applicable_scope_json`、`learning_candidate_id`、`status`

- 现有独有（保留，不删）：`business_ref_id`、`business_ref_type`、`confidence`、`coverage`、`defect_count`、`description`、`entity_key`、`entity_type`、`metadata_json`、`name`、`plan_summary`、`project_id`、`review_status`、`risk`、`source_id`、`summary`、`task_id`、`title`、`verdict`

- **迁移策略**：新建 `bug_patterns`（仅 approved 进入）。`knowledge_entity` 是知识图谱实体，语义不同，不复用。

- **预估迁移脚本行数**：≈ 70（Alembic revision + 索引 + 回填）


### 4.20 `noise_suppression_rules`

**目标字段**（13 号 §4.20）：14 个 — `id`、`scope`、`scope_ref`、`category`、`match_condition_json`、`effective_from`、`effective_until`、`owner_id`、`reason`、`linked_issue_ref`、`evidence_refs_json`、`action`、`last_reviewed_at`、`renewal_of_rule_id`

**现有候选**：无同义表（新建）


**差异**：同名字段 0 / 目标新增 14 / 现有独有 0

- 目标新增（需 ALTER 或新表）：`id`、`scope`、`scope_ref`、`category`、`match_condition_json`、`effective_from`、`effective_until`、`owner_id`、`reason`、`linked_issue_ref`、`evidence_refs_json`、`action`、`last_reviewed_at`、`renewal_of_rule_id`

- **迁移策略**：新建 `noise_suppression_rules`（≤90 天 + 续期自引用）。现有无规则表。

- **预估迁移脚本行数**：≈ 95（Alembic revision + 索引 + 回填）


### 4.21 `project_adapters`

**目标字段**（13 号 §4.21）：11 个 — `id`、`project_id`、`adapter_key`、`adapter_yaml_ref`、`capabilities_yaml_ref`、`prompt_profile_yaml_ref`、`platforms_json`、`schema_version`、`checksum`、`created_at`、`updated_at`

**现有候选**：

- `project`：**不存在**（审计脚本未找到该表）


**差异**：同名字段 0 / 目标新增 11 / 现有独有 0

- 目标新增（需 ALTER 或新表）：`id`、`project_id`、`adapter_key`、`adapter_yaml_ref`、`capabilities_yaml_ref`、`prompt_profile_yaml_ref`、`platforms_json`、`schema_version`、`checksum`、`created_at`、`updated_at`

- **迁移策略**：新建 `project_adapters`（指向 adapter/capabilities YAML）。现有 `project` 表只存项目元数据，不合并。

- **预估迁移脚本行数**：≈ 80（Alembic revision + 索引 + 回填）


### 4.22 `node_capability_manifests`

**目标字段**（13 号 §4.22）：11 个 — `id`、`node_id`、`driver_key`、`driver_version`、`capabilities_json`、`platforms_json`、`max_parallel_sessions`、`artifact_types_json`、`last_evidence_ref`、`last_heartbeat_at`、`available`

**现有候选**：

- `runner_execution_task`（RunnerExecutionTask，test-platform-v2/backend/app/models/runner_execution.py，14 列）：`id`、`project_id`、`environment_id`、`task_id`、`runner_key`、`request`、`assertions`、`status`、`result`、`error_message`、`locked_at`、`locked_by`、`claimed_at`、`finished_at`

- `execution_jobs`（ExecutionJob，test-platform-v2/backend/app/models/execution_job.py，19 列）：`id`、`project_id`、`kind`、`status`、`case_refs_json`、`payload_json`、`env_ref`、`attempt`、`timeout_seconds`、`node_id`、`claimed_at`、`lease_expires_at`、`heartbeat_at`、`started_at`、`finished_at`、`evidence_bundle_id`、`result_json`、`summary`、`error_message`


**差异**：同名字段 2 / 目标新增 9 / 现有独有 25

- 同名（可直接复用）：`id`、`node_id`

- 目标新增（需 ALTER 或新表）：`driver_key`、`driver_version`、`capabilities_json`、`platforms_json`、`max_parallel_sessions`、`artifact_types_json`、`last_evidence_ref`、`last_heartbeat_at`、`available`

- 现有独有（保留，不删）：`assertions`、`attempt`、`case_refs_json`、`claimed_at`、`env_ref`、`environment_id`、`error_message`、`evidence_bundle_id`、`finished_at`、`heartbeat_at`、`kind`、`lease_expires_at`、`locked_at`、`locked_by`、`payload_json`、`project_id`、`request`、`result`、`result_json`、`runner_key`、`started_at`、`status`、`summary`、`task_id`、`timeout_seconds`

- **迁移策略**：新建 `node_capability_manifests`；`runner_execution_task`/`execution_jobs` 的节点信息（`node_id/lease/heartbeat`）是调度态，不是能力清单，不复用。

- **预估迁移脚本行数**：≈ 80（Alembic revision + 索引 + 回填）

---

## 6. 服务层对账（13 号 §18.5 的 8 个接入点）

| # | 规格接入点 | 现状文件 | 存在 | 审计结论 |
|---|-----------|---------|:----:|---------|
| 1 | LLM 直连 | `app/services/ai_client.py`、`ai_config_service.py` | ✅ | 直连可用；删除 `ai_gateway/` 后需确认 `ai_client` 的 provider pool 覆盖 4 把 Key |
| 2 | Skill 注入 | `app/services/ai_service.py`（`_load_skill_context_for()` L61） | ✅ | 现为**固定 kind**（functional/…），需扩成按项目 profile 动态加载 |
| 3 | 需求导入 | `requirement_service.py`、`openapi_import_service.py` | ✅ | 导入产物落 `requirement_document` + `api_endpoint`；契约冻结需新增 version/checksum |
| 4 | Playwright 执行 | `playwright_executor.py` | ✅ | 仍在控制面（subprocess），batch-277 迁 node；`cameltv_node` 已有 web 执行腿 |
| 5 | 证据 | `evidence_bundle_service.py` | ✅ | 已做 sha256 manifest 对账 + 完整率判定（消费 `execution_runtime.completeness`），可直接复用到 Artifact |
| 6 | 缺陷 | `defect_service.py` + `defect*` 4 表 | ✅ | 需加 `linked_ac_id/triage_case_id/fixed_commit_sha` + retest 方法 |
| 7 | 节点协议 | `app/modules/campaign_execution/contracts.py` | ✅ | `ExecutionJobKind = api/ui/script/external`；AIQE 需扩 `dag_node` 等新 kind（或独立表，见 §9） |
| 8 | 节点运行时 | `scripts/node/cameltv_node/` | ✅ | 注册/心跳/认领/执行/证据上传**已完整**；缺 `db` 只读与事件上报 |

**附加相关服务（规格未列但必须知晓）**：

| 服务 | 作用 | 与 AIQE 关系 |
|------|------|-------------|
| `execution_job_service.py` | 建/认领/心跳/回收/上报任务（`create_job/claim_job/heartbeat/report/reclaim_stale/node_status/list_nodes`） | `node_runs.execution_job_id` 1:1 绑定；**复用**调度语义 |
| `version_task_exec_service.py` | 版本任务条目执行（HTTP 断言） | 同步执行器；M1 作为 `source_type=version_task` 适配 |
| `ui_test_service.py` | `/uitest` 任务编排 + 控制面 playwright | batch-277 剥离浏览器 |
| `runner_execution_task` 模型 | 外部 runner 任务（request/assertions/result） | `kind=external` 的持久化载体，保留 |

---

## 7. 路由层对账（规格 §15.2 的 30 个端点）

**现状**：265 paths / 323 operations / 27 个业务段；`/api/v1/aiqe/` **0 条**（新前缀未建）。

| 规格分组 | 端点数 | 现有可直接复用 | 需新建 | 说明 |
|---------|:-----:|:-------------:|:-----:|------|
| 需求契约 | 5 | 0 | 5 | 现有 `/requirements` 是导入/评审，无 contract/analyze/freeze/diff |
| 用例 / 场景 | 4 | **1**（`POST /test-cases/{case_id}/review`） | 3 | `GET /requirements/{document_id}/coverage` 是文档级覆盖，**非** case 级 |
| Workflow | 4 | 0 | 4 | 无 workflow 实体与端点 |
| Runs | 11 | 0 | 11 | 无通用 `/runs`；`/open/runs/{run_id}` 是外部只读投影 |
| Triage | 2 | 0 | 2 | 无 |
| 回归 | 2 | 0 | 2 | `POST /release-bundles/{id}/trigger-regression` 是发布包级触发，语义不同 |
| Learning | 2 | 0 | 2 | 无 |
| **合计** | **30** | **1** | **29**（含 1 个需改造） | 净新增工作量大，排期需覆盖 |

---

## 8. 前端对账（规格 §18.2）

| 维度 | 规格建议 | 实际 | 结论 |
|------|---------|------|------|
| 目录结构 | `src/features/{runs,triage,regressions,workflows,requirement-contracts,profiles}/` | `src/pages/<domain>/` 19 个域 | **改口径**：在 `pages/runs/`、`pages/triage/`、`pages/regressions/` 落地，不新建 `features/` |
| 页面组件 | 6 个页面 | 153 个页面组件 | 复用现有 `PageLoader` + `pages/` 懒加载模式 |
| 路由 | `/runs`、`/runs/:id` … | 30 条路由（含 3 条 `version-tasks`） | 按 batch-276 D-6：保留 `/version-tasks`，新增 `/runs` |
| 组件复用 | `RunHeader/RunGraph/RunTimeline/ArtifactViewer/useRunEvents` | 现有 `ui/` 组件库 + `hooks/` | 新组件放 `pages/runs/components/`，通用件下沉 `ui/` |

---

## 9. Driver / Node 现状与能力表

| 能力 | 现状 | 证据 | AIQE 要用时怎么做 |
|------|------|------|------------------|
| 节点注册 | ✅ | `cli.py` `POST` 注册（`agent_id + capabilities`） | 复用；capability 清单扩 `ui.overlay.observe/control` |
| 心跳 / 租约 | ✅ | 30s 心跳；`execution_job_lease_seconds`（默认 300s） | 复用；`node_runs` 记录 heartbeat 快照 |
| 任务认领 / 回收 | ✅ | `claim_job`、`reclaim_stale`（`attempt+1`） | 复用；租约过期语义映射到 `node_runs.status` |
| API 执行 | ✅ | `executor.py` `api` kind（httpx + `$` 取值 + 断言） | 复用为 `http` Driver 的执行腿 |
| Web 执行 | ✅ | `executor.py` `web` kind（Playwright + 步骤解释器，截图/console） | 复用为 `playwright` Driver 的执行腿 |
| 证据上传 | ✅ | `evidence.py` sha256 manifest + 平台对账 | 直接作为 `run_artifacts` 的入库通道 |
| DB 只读 Driver | ❌ | 无 | TA-014 新建（`db_readonly_driver`） |
| 事件流（seq/SSE） | ❌ | 无事件表、无 SSE | TA-006 新建（`run_events` + outbox + SSE） |
| 跨端（Android / 小程序） | ❌ | 无 | V1.1+（TA-039/040） |
| 设备/真机池 | ❌ | 无 | V1.1+ |

**结论**：节点侧是**现有资产最厚的部分**；AIQE 缺的是**控制面的事实层（Run/Event/Artifact）**，不是执行腿。

---

## 10. 现有执行链时序（三条真实链路）

### 链 A：版本任务（同步循环，无节点/无事件）

```text
POST /version-tasks/{id}/run
  → version_task_service.start_run()
      task.status: approved|draft → executing
      VersionTaskRun(status=running, progress=0)         ← 1 行汇总记录
      for item in adopted_items:                          ← 同步阻塞，无 Job
          version_task_exec_service.execute_item(item)     ← HTTP 断言，结果进内存
              → evidence[] / failures[] / passed|failed|skipped|blocked
      VersionTaskRun(progress=total, evidence=json, failures=json)
      task.status: executing → executed
  错误路径：execute_item 抛错 → 整个 API 请求失败（无 per-item 隔离）
  取消路径：任务状态机有 cancelled，但执行中的循环**不可中断**
```

### 链 B：节点执行（有租约/心跳/回收）

```text
POST /execution-jobs  → ExecutionJob(status=pending, attempt=0, lease=nil)
POST /execution-jobs/claim (node_id)  → status=running, lease_expires_at=now+300s
  cameltv-node: HeartbeatThread 每 30s POST /execution-jobs/{id}/heartbeat（续租）
  执行 kind=api|ui|script|external → 产物落本地 evidence 目录
  POST /execution-jobs/{id}/report → status=completed|failed|cancelled + evidence
  错误路径：节点崩溃 → 不续租 → 平台 reclaim_stale() → pending(attempt+1) → 重派
```

### 链 C：/uitest（控制面 subprocess）

```text
POST /ui-tests/jobs → UiTestJob → UiTestRun(status=running)
  ui_test_service → playwright_executor（subprocess: npx playwright test）
      → storage/ui-runs/<run>/screenshots|trace|html report
  UiTestRun(status/result/artifacts) → 前端展示
  错误路径：超时 kill 进程树；取消轮询 cancel_requested
```

**AIQE M1 的定位**：新建第四条链（Run/Node/Event/Artifact），把 A/B/C 作为 `source_type` 适配进来；**不替换**任何一条现有链。

---

## 11. 迁移批次建议

| 阶段 | 表 | 依据 | 预估行数 |
|------|----|------|---------|
| **M1（batch-279/280/281）** | `test_runs`、`node_runs`、`step_attempts`、`assertion_results`、`run_events`、`event_outbox`、`run_artifacts`、`execution_profiles` + ALTER `environments` | 11 号 §0 P0-2 的"可逆迁移"要求；先把事实层立起来 | 见下表汇总 |
| **M2（batch-283+）** | `workflow_definitions` + `test_runs.workflow_definition_id` 生效 | DAG 需要先有 Run 容器 | — |
| **M3（batch-289+）** | `requirement_contracts`、`acceptance_criteria`、`test_scenarios` + ALTER `test_cases` | Agent 需要契约与场景实体 | — |
| **M4（batch-295+）** | `interference_observations`、`triage_cases`、`triage_hypotheses`、`regression_requests` + ALTER `defects` | 归因/回归闭环 | — |
| **M5（batch-300+）** | `agent_executions`、`learning_candidates`、`bug_patterns`、`noise_suppression_rules`、`project_adapters`、`node_capability_manifests` | 学习与多项目 | — |

**M1 迁移顺序（强依赖）**：
1. `environments` ALTER（Run 需要 `base_urls_json` / `data_sources_json`）；
2. `execution_profiles`（Run 启动前选择）；
3. `test_runs`（UUID PK + `environment_id BIGINT`）；
4. `node_runs`（`run_id UUID` + `execution_job_id BIGINT`）；
5. `step_attempts`、`assertion_results`；
6. `run_events` + `event_outbox`（同事务写，唯一索引 `(run_id, seq)`）；
7. `run_artifacts`（`storage_uri` + sha256）；
8. 回填：把 `version_task_run` 历史 N 行映射为 `test_runs(source_type=version_task)`，写 `legacy_version_task_run_id`。

**迁移硬规则**：每个 revision 必须**升/降都可执行**（§0 P0-2），`DROP/ALTER` 带存在性守卫；SQLite + PG 双端 CI 各跑一次。

---

## 12. 不冲突项打钩（DoD 清单）

| 检查项 | 结论 | 证据 |
|--------|:----:|------|
| §18.5 的 8 个接入点全部存在 | ✅ | §6 表，8/8 `Test-Path` 通过 |
| `execution_jobs` 可与 `node_runs` 1:1 绑定 | ✅ | `execution_jobs.id INT` + `kind/status/lease/heartbeat` 字段齐 |
| `defect` / `environment` / `test_case` 可 ALTER 扩展 | ✅ | 三表均有 `project_id INT`，目标字段是增量 |
| 蓝湖证据表独立、不被 Run 证据覆盖 | ✅ | `lanhu_evidence_*` 4 表 + §4.12 D-5 边界规则 |
| 节点协议无需重写 | ✅ | `cameltv_node` 注册/心跳/认领/证据上传完整 |
| ai_* 删除清单准确 | ✅ | `ai_gateway/` 8 文件 + 3 model 文件在位 |
| SQLite/PG 双端迁移路径可行 | ✅ | 附录 C + 现有 118 revisions 均双端可跑 |
| ID 类型口径 | ⚠️ 待确认 | C-01：新建 UUID / 现有 FK BIGINT |
| 30 个 REST 端点工作量 | ⚠️ 待确认 | 29 个净新增，排期需含 |
| 前端目录口径 | ⚠️ 待确认 | C-09/§8：用 `pages/` 而非 `features/` |

---

## 13. 待用户确认的决策（3 条）

| ID | 决策点 | 决定（2026-11-09 用户确认） | 落地位置 |
|----|-------|---------------------------|---------|
| **D-278-1** | ID 类型口径 | **新建实体 UUID + 现有表外键 BIGINT**（§3 C-01） | 13 号 §4 关键规则（v1.3） |
| **D-278-2** | `version_task_run` 迁移路径 | **候选 B：保留旧表 + `test_run_id BIGINT` 回填，M2 后只读，V1.1 删表** | 13 号 §4.7 迁移策略（v1.3） |
| **D-278-3** | 前端目录 | **沿用 `pages/<domain>/`，不建 `features/`** | 13 号 §18.2 目录树 + 目录决策（v1.3） |

> 三条决策已确认并回写 13 号 `v1.3-baseline-aligned`（batch-278 决策回写批次）；C-278-1（模型 ID 类型守卫）/ C-278-2（`test_run_id` 回填率 100% 才可切只读）随 batch-279 登记。

---

## 14. 附录：证据与命令

```powershell
# 1) 模型清单（AST 解析，不导入 ORM；脚本见 dev-plan §2）
#    产出：表名 / class / 列数 / 主键类型 / ForeignKey

# 2) 真实路由（导入 app.main 导出 OpenAPI）
$env:DATABASE_URL='sqlite:///./data/ta001-audit.db'; $env:ENVIRONMENT='test'
python -c "from app.main import app; s=app.openapi(); print(len(s['paths']))"   # 265

# 3) 计数
(Get-ChildItem app/models -Filter *.py).Count                                   # 43
(Get-ChildItem app/services -Filter *.py).Count                                 # 71
(Get-ChildItem app/services -Recurse -Filter *.py).Count                        # 123
(Get-ChildItem app/api/v1 -Filter *.py).Count                                   # 45
(Get-ChildItem alembic/versions -Filter *.py).Count                             # 118
(Get-ChildItem ../frontend/src/pages -Directory).Count                          # 19
```

**审计产物**：本文件 + batch-278 六件工件（PRD / PM / Design / Dev / QA / Leader verdict）+ 看板。

**已知缺口**（不在 TA-001 范围）：`app/services/` 123 个文件只按 8 个接入点抽查，未做逐文件依赖图；前端 153 个页面组件未做逐页归属；这两项留给 TA-004（模型映射表）/ M5 前端改造时补。
