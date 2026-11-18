# AIQE v1.5 AUD 整改基线映射（PR-AUD-00）

> 基线：`origin/main` = `b0f6cdd4ccc3f54dc762873a5d01ab7c9e07f1a3`（2026-11-14，"docs(aiqe): 使用与项目接入指南 + 引导脚本 (#596)"）。
> 分支：`feature/aiqe-v15-aud-remediation`（独立 worktree，DeepSeek_Harness / direct）。
> 依据：`CamelTv_AIQE_AUD_Remediation_v1.5_Full.md`（v1.5，2026-11-18）+ `docs/platform-refactor/13-ai-quality-agent-merged-spec.md`。
> 本文是 v1.5 §07 `PR-AUD-00` 要求的"基线刷新 + 代码映射"交付物：**只记录可复核事实**，每条结论都可由文件路径 / 命令复现。

## 0. 结论摘要

| 批次 | AUD | 现状 | 本轮是否已整改 |
|---|---|---|---|
| 第一批 | AUD-001 SSRF/Redirect/DNS | 缺失（HTTP Driver 自动跟随跳转、无目标策略） | ✅ 已交付 |
| 第一批 | AUD-002 DB Query Registry | 部分（只读 SQL 校验存在，无登记/项目注入/超时） | ✅ 已交付 |
| 第一批 | AUD-003 Secret 全链路 | 部分（headers 脱敏，输出/持久化无分类器） | ✅ 已交付 |
| 第一批 | AUD-004 实验→真 Run | **违规**（`uuid4()` 伪造 verification_run_id + 直接 completed） | ✅ 已交付 |
| 第一批 | AUD-005 Capability/Preflight | 部分（boolean available，无 VERIFIED 状态、无 Preflight） | ✅ 已交付 |
| 第一批 | AUD-006 状态一致性/恢复 | 部分（lease/fencing 无、事件无生产者、Reconciler 无） | ✅ 已交付 |
| 第二批 | AUD-007 Assertion Engine | **缺失**（断言写死在 node_executor，`run_assertion_results` 零写入） | ✅ 已交付 |
| 第二批 | AUD-008 Artifact 生命周期 | 部分（模型+存储+GC 有，无 Upload/Download API、无 Viewer、GC 硬删） | ✅ 已交付 |
| 第二批 | AUD-009 Regression 幂等/SHA | **缺失**（`min_length=7`、无 fingerprint、无 deployed SHA） | ✅ 已交付 |
| 第二批 | AUD-010 Regression 终态/对比 | **缺失** | ✅ 已交付 |
| 第二批 | AUD-011 Mixed Workflow Dogfood | **缺失**（占位 E2E 只断言 body.count()==1） | ✅ 已交付 |
| 第二批 | AUD-012 Defect Draft 可复现 | 部分（草稿服务存在，evidence 仅前缀字符串校验） | ✅ 已交付 |
| 第三批 | AUD-013 A0–A6 Registry/Orchestrator | **缺失**（无 AgentProtocol/AgentResult/Registry/DAG） | ✅ 已交付 |
| 第三批 | AUD-014 Requirement Contract | **缺失**（无 Contract 表/状态机/source ref 解析） | ✅ 已交付 |
| 第三批 | AUD-015 结构化 Case | **缺失**（无 automation_grade/covers_ac_ids/oracle_ref） | ✅ 已交付 |
| 第三批 | AUD-016 A4 Evidence-grounded | 部分（schema 校验有，evidence 不做服务端解析） | ✅ 已交付 |
| 第三批 | AUD-017 A5 影响图 | 部分（文件名子串规则，无 git diff/symbol/trace path） | ✅ 已交付 |
| 第三批 | AUD-018 A6 Benchmark | **违规**（接受前端自报 false_positive_rate） | ✅ 已交付 |
| 第三批 | AUD-019 Noise Intelligence | 部分（10 个资源 Detector ≠ 12 类目；无 Observation 表） | ✅ 已交付 |
| 第三批 | AUD-020 多端真实 Driver | 部分（boolean available；iOS 硬关闭；无 PlatformBinding） | ✅ 已交付（代码侧） |

## 1. 基线事实

| 项 | 事实 |
|---|---|
| Commit | `b0f6cdd4ccc3f54dc762873a5d01ab7c9e07f1a3` |
| Alembic head | `20261123_ta033_mutation_ledger`（单 head；本轮新增 `20261124_aud001_target_policy`） |
| 后端入口 | `test-platform-v2/backend/app/main.py`；AIQE 路由 `app/api/v1/aiqe_*.py`（前缀 `/api/v1/aiqe`） |
| AIQE 目录 | `app/aiqe/{models,services,drivers,agents,adapters,security}` |
| AIQE 测试 | `tests/test_aiqe_*.py`（45 个模块）+ `tests/e2e/aiqe/` |
| 远端可达性 | 2026-11-18 本机 `git fetch` 无法连接 github.com:443（代理不可用），基线取本地 `origin/main`；如远端有新提交需重新 fetch 后复核 |

### 1.1 复现命令

```powershell
cd test-platform-v2/backend
python -m alembic heads
python -m pytest tests/ -q -k "aiqe" --ignore=tests/e2e   # 基线 461 passed
rg "append_event\(" app/                                  # 仅 event_service 定义
rg "RunAssertionResult\(" app/                            # 仅模型
rg "put_artifact\(" app/                                  # 仅定义
rg "verification_run_id=.*uuid" app/aiqe                  # triage_service.py:73 伪造
```

## 2. AUD-001（已交付）

**问题**：`HttpDriver` 使用 `httpx.Client(follow_redirects=True)`，目标 URL 完全由 Workflow 节点输入决定，无 host/端口/方法/私网策略，不校验 DNS 实际地址，跨主机跳转无条件跟随。

**交付**：

| 文件 | 作用 |
|---|---|
| `app/aiqe/models/security.py` | `TargetPolicyRecord`（`aiqe_target_policies`，项目/环境级、带 version、active） |
| `alembic/versions/20261124_aud001_target_policy.py` | 迁移（幂等：已存在表则跳过，可 downgrade） |
| `app/aiqe/security/target_policy.py` | `TargetPolicy`（不可变快照）、`TargetPolicyResolver.resolve(project_id, environment_id)`（只读服务端配置，拒绝调用方覆盖）、`upsert_target_policy`（版本乐观锁） |
| `app/aiqe/security/safe_target.py` | `SafeTargetValidator`：scheme/userinfo/端口/方法/主机白名单（`*.suffix`）/DNS 全地址校验/私网与保留段/混淆数字写法/zone id/IDNA；`validate_redirect` 逐跳重校验 |
| `app/aiqe/security/dns_pin.py` | `pinned_dns`：请求期间把主机固定到已验证 IP（DNS Rebinding 防护） |
| `app/aiqe/security/safe_http.py` | `SafeHttpExecutor.request()`：校验先行、`follow_redirects=False` 手动逐跳、请求/响应限额、`policy_version` + `target_resolution_snapshot` 证据、拒绝返回 `blocked` |
| `app/aiqe/services/node_executor.py` | http 节点统一走 `SafeHttpExecutor`；节点输入的 `allow_private/allowed_hosts/...` 被忽略并留痕；策略拒绝 → `BLOCKED`；playwright 导航同样先校验 |
| `tests/test_aiqe_aud001_target_policy.py` | 46 条：13 类私网/混淆地址、8 类非法 URL、白名单/端口/方法、DNS 多地址、DNS rebinding、Redirect 私网/跨主机/上限/307/302、响应截断、请求体上限、真实本地 HTTP 服务端到端、节点级与安全事件可追踪 |

**默认值**：未配置策略 = `deny_all`；私网/回环需 `allow_private_cidrs` 显式授权；`blocked_cidrs`（169.254/16、100.64/10、0/8、240/4、fe80::/10、64:ff9b::/96 等）任何策略都不能放行；默认 `max_redirects=0`。

**未覆盖（后续）**：Runner 侧 egress 防火墙与容器网络 deny-by-default 属于 DevOps 交付；`proxy_profile_id` 字段尚未接入（当前策略强制直连）。

## 2.1 AUD-002（已交付）

**问题**：`DbReadonlyDriver` 只有应用层 SQL 关键字过滤；Workflow 可传任意 SQL、任意连接、任意表；无 `project_id` 注入、无行/时间限额、无结果脱敏。

**交付**：

| 文件 | 作用 |
|---|---|
| `app/aiqe/models/query_registry.py` + 迁移 `20261124_aud002_query_registry` | `aiqe_registered_queries`（project + query_key + version 唯一、statement/params/limits/schema/审批字段） |
| `app/aiqe/services/query_registry.py` | `register_query`（只允许单条 SELECT/WITH；拒绝 DDL/DML/多语句/FOR UPDATE/INTO/系统目录/文件函数；必须含 `:project_id`；参数集合精确匹配）、`resolve_query`（按项目+key+version）、`DbReadonlyExecutor`（服务端注入 `project_id`、参数化绑定、`max_rows`、`max_execution_ms`、生产环境默认拒绝、连接只从 `AIQE_DB_READONLY_URLS` 解析）、结果摘要（query_hash / rows_digest / 脱敏参数）与敏感列脱敏 |
| `app/aiqe/services/node_executor.py` | `db` driver 只接受 `query_key + params`；`sql/connection_url/allowed_tables/...` → `BLOCKED WORKFLOW_DB_OVERRIDE` |
| `app/aiqe/drivers/db_readonly_driver.py` | PostgreSQL `SET LOCAL statement_timeout` |
| `app/core/config.py` | `aiqe_db_readonly_urls` 服务端连接引用表 |

**测试**：`tests/test_aiqe_aud002_query_registry.py`（28 条：登记负向 8 类语句、参数匹配、版本解析、跨项目拒绝、服务端注入、字符串注入不改结构、行数上限、生产环境拒绝、连接未配置、节点级覆盖拒绝）。

## 2.2 AUD-003（已交付）

**问题**：`job_consumer` 把 `result.detail`（含完整请求头/响应体）写入 `node_runs.output_ref` 与 `step_attempts.output_summary_json` → 登录节点的 `access_token` 明文落库；无共享分类器；无 Secret Handle。

**交付**：

| 文件 | 作用 |
|---|---|
| `app/aiqe/redaction.py` | 唯一 `SensitiveDataClassifier` / `Redactor`：字段名规则 + JWT/Bearer/PEM/AKIA/sk-/canary 值模式、JSON 感知文本脱敏、`assert_no_secret` fail closed |
| `app/aiqe/services/dag_scheduler.py` | `complete_node` 写入前脱敏（含 `_finalize_attempt`） |
| `app/aiqe/services/job_consumer.py` | `job.result_json` 脱敏 |
| `app/aiqe/services/event_service.py` | `append_event` 载荷脱敏 |
| `app/aiqe/models/secret_handle.py` + 迁移 `20261124_aud003_secret_handles` | `aiqe_secret_handles`（只存 `vault://` 引用 + scope + TTL + 撤销） |
| `app/aiqe/services/secret_vault.py` | 进程内 Vault；`create/resolve/revoke` 强制 project+run+consumer 白名单+TTL+撤销 |
| `app/aiqe/services/run_context.py` | `set_output_secure`（敏感输出→Handle 引用）、`resolve_inputs`（`${nodes.x.outputs.y}` / `${secret_handles.id}` 按 consumer scope 解析） |

**测试**：`tests/test_aiqe_aud003_secret_protection.py`（44 条：字段名/值模式、递归脱敏、**端到端 canary**——真实本地 HTTP 服务返回 `CANARY_SECRET_*`，扫描 node_runs/step_attempts/execution_jobs/run_events 明文命中 0，且 `match_id/status` 仍可追溯；Handle 合法/跨 Run/跨 Project/非白名单/过期/撤销全路径）。

## 2.3 AUD-004（已交付）

**问题**：`triage_service.run_experiment` 用 `uuid4()` 伪造 `verification_run_id` 并直接 `status="completed"`；E1–E6 语义与 v1.5 §04 表格不符。

**交付**：

| 文件 | 作用 |
|---|---|
| `app/aiqe/services/triage_service.py` | `ExperimentSpec` 矩阵（E1 run_attempt / E2 fixture_namespace / E3 upstream_mode / E4 feature_flag / E5 worker_instance / E6 network_profile）、`validate_change` 绑定唯一变量、`create_experiment`（必须真实 baseline Run，停在 VALIDATED）、`launch_experiment`（统一路径创建真实 `TestRun` + 复制节点骨架 + 单变量快照 diff；多变量 → BLOCKED）、`sync_experiment_result`（仅 Run 终态后 COMPLETED；Run 丢失 → UNKNOWN）、`record_experiment_result`（仅 COMPLETED 可记 SUPPORTED/REFUTED/INCONCLUSIVE） |
| `app/aiqe/models/triage.py` + 迁移 `20261124_aud004_experiment_run_binding` | 新增 project_id / baseline_run_id / changed_dimension / snapshot hash / diff / result / error_code / started_at / completed_at |

**测试**：`tests/test_aiqe_triage_experiments.py`（20 条，**已重写**：删除断言"随机 UUID 即验证 Run"的旧用例，新增真实 Run 绑定、幂等、多变量 BLOCKED、终态收敛、Run 丢失 UNKNOWN）。

## 3. 第一批剩余缺口（按代码事实）

> AUD-001…AUD-006 均已交付（见 2.1–2.3、3.1–3.3）。第一批无剩余 P0 缺口。
> 仍属 DevOps 交付、不在代码范围：Runner 出口防火墙 / 容器网络 deny-by-default、真实浏览器/设备节点注册。

### 3.1 AUD-005（已交付）

**问题**：`NodeCapabilityManifest.available: bool` 无法区分 REGISTERED / AVAILABLE / VERIFIED；无 Preflight，缺少能力时执行期才 `UNSUPPORTED_DRIVER`。

**交付**：

| 文件 | 作用 |
|---|---|
| `app/aiqe/models/capability.py` + 迁移 `20261124_aud005_capability_status` | 6 态 `capability_status`、`verified_platforms_json`、`verified_at`、`runner_version`/`manifest_version`/`manifest_signature`、`status_reason`；`available` 保留为派生投影 |
| `app/aiqe/services/capability_registry.py` | `compute_effective_status`（心跳新鲜度）、`mark_verified`（必须真实平台+证据）、`invalidate_verification`（软件更新降级）、`mark_degraded`/`revoke`/`restore`、`select_nodes` 仅可调度状态、`platform_matrix` |
| `app/aiqe/services/preflight.py` | driver→能力映射、生产环境守卫、单节点/整图 preflight、`schedule_guard`；进程内 http/db 不要求外部节点 |
| `app/aiqe/services/dag_scheduler.py` | `schedule(preflight=...)`：不可执行节点直接 BLOCKED 且**不创建 ExecutionJob** |
| `app/aiqe/services/job_consumer.py` | 执行前预检，`PREFLIGHT_BLOCKED` 落节点 blocker |

**测试**：`tests/test_aiqe_aud005_capability_preflight.py`（21 条：6 态、软件更新降级、心跳过期、DEGRADED/REVOKED、平台不匹配、生产守卫、整图 blocker、缺能力不建 Job）。

### 3.2 AUD-006（已交付）

**问题**：无 fencing token（旧 Worker 迟到结果可覆盖新结果）；`append_event` 无生产调用（Run 时间线恒空）；无 Reconciler（Worker kill 后 Run 可能永久 RUNNING）。

**交付**：

| 文件 | 作用 |
|---|---|
| `app/aiqe/models/run.py` + 迁移 `20261124_aud006_fencing_token` | `node_runs.fencing_token` / `step_attempts.fencing_token` |
| `app/aiqe/services/lease.py` | `LeaseContext`、`assert_current`（token + 租约有效期）、`bump_fencing_token`、`StaleLeaseError`/`LeaseExpired` |
| `app/aiqe/services/job_consumer.py` | 认领时以"下一次 attempt"为唯一 token 来源并提升节点 token；`run_job`/`complete_from_report` 写前校验 token，迟到上报返回 `STALE_LEASE` |
| `app/aiqe/services/dag_scheduler.py` | `complete_node(fencing_token=...)` 拒绝旧 token；生产 `node.ready/node.started/node.completed|failed|blocked/node.retry_scheduled/node.lease_expired/run.completed` 事件（幂等 producer_event_id）；`finalize_run()` |
| `app/aiqe/services/reconciler.py` | 过期租约 Job → 节点 requeue（上限后 BLOCKED）、token 提升、Run 收口、实验同步；`AIQE_RECONCILER_ENABLED` 后台线程 |

**测试**：`tests/test_aiqe_aud006_state_recovery.py`（15 条：token 提升/拒绝、租约过期、Worker kill→requeue→新 Job、超限 BLOCKED→Run INCOMPLETE、迟到结果拒绝、事件生命周期、重复投递幂等）。

### 3.3 AUD-007（已交付）

**问题**：断言逻辑内联在 Driver（`expected_status`/`expect_text`）；`run_assertion_results` 零写入；Driver 成功即 Run PASS。

**交付**：

| 文件 | 作用 |
|---|---|
| `app/aiqe/assertions/observation.py` | 结构化 `Observation` + JSONPath 子集（拒绝通配/递归） |
| `app/aiqe/assertions/registry.py` | 有版本 `OperatorSpec`：equals/not_equals/contains/exists/regex/in/gte/lte/json_schema（按 JSON Pointer 报错） |
| `app/aiqe/assertions/engine.py` | P0/P1 无 Oracle → BLOCKED；缺失值 → FAIL/UNKNOWN 不 PASS；evaluator 异常 → ERROR；Driver 失败 → NOT_EVALUATED；required-only 聚合；`poll_until`（有 timeout 与采样） |
| `app/aiqe/models/run.py` + 迁移 `20261124_aud007_assertion_fields` | `run_assertion_results` 增加 oracle_*/evaluator_*/source_ref/required/duration_ms/evaluated_at |
| `app/aiqe/services/result_writer.py` | 唯一断言写入口（attempt+key 幂等）、聚合→节点终态、`assertion.evaluated` 事件 |
| `app/aiqe/services/job_consumer.py` | 有断言时以断言结论覆盖 Driver 结论（HTTP 200 + 业务错误 → FAIL） |
| `app/api/v1/aiqe_runs.py` | `GET /api/v1/aiqe/runs/{run_id}/assertions`（含 Oracle/evaluator/expected/actual） |

**测试**：`tests/test_aiqe_aud007_assertion_engine.py`（26 条：算子矩阵、Schema JSON Pointer、缺失值语义、P0 Oracle 门禁、evaluator 异常、聚合优先级、轮询、真实服务 200+业务错误端到端落库、接口 RBAC/项目隔离）。

## 4. 第二批缺口要点

- AUD-007：✅ 已交付（见 3.3）。
- AUD-008：✅ 已交付 —— `run_artifacts` 增加 project_id/规范 ArtifactType/上传状态/保留期/墓碑；两阶段上传（`create_pending_artifact` → `complete_upload`，服务端重算 sha256，不匹配 CORRUPTED 且不落存储）；`open_download` 重新鉴权并拒绝未完成/损坏/已清理；GC 改为墓碑（`PURGED` + `deleted_at` + metadata，行保留）；`_finalize` 在有 PENDING/CORRUPTED 证据时 Run 只能 INCOMPLETE；新增 `/api/v1/aiqe/artifacts` 路由（会话/上传/元信息/下载 + RBAC + `Cache-Control: private`）。测试 `tests/test_aiqe_aud008_artifact_lifecycle.py`（16 条）。
- AUD-009：✅ 已交付 —— `aiqe_deployment_attestations` 可信部署记录；`fixed_sha` 必须 40 位；部署缺失/不匹配 → BLOCKED（不启动 Run）；服务端 fingerprint 唯一约束实现幂等；范围冻结（直接失败节点/断言 + P0 选择，排除项有 reason）；验证 Run 复制 source 节点骨架；新入口 `POST /api/v1/aiqe/defects/{defect_id}/regressions`。
- AUD-010：✅ 已交付 —— `run_comparison_snapshots`（只追加）；`regression_terminal.handle_run_terminal` 幂等收敛（断言聚合、建议 `READY_FOR_HUMAN_CLOSE`/`NEEDS_MORE_FIX`/`INCONCLUSIVE`，**不自动关闭缺陷**）；`consume_terminal_events` 消费 outbox `run.completed`；`GET /regressions/{id}/comparison` 懒收敛；`POST /regressions/{id}/cancel`。测试 `tests/test_aiqe_regression_api.py`（14 条，已重写为强化契约）。
- AUD-011：✅ 已交付 —— `services/dogfood.py`（真实 node_executor/Target Policy/Query Registry/Assertion Engine/Secret Handle 的执行循环；`${base}` 与 `${nodes.*}` 递归解析；每轮由调度器推进 READY；外部 UI Driver 走 Preflight，无 VERIFIED Runner 即 BLOCKED）；`scripts/aiqe/run_dogfood_mixed.py` CLI（缺配置退出码 2，不伪造 PASS）。测试 `tests/test_aiqe_aud011_dogfood_mixed.py`（7 条，真实本地 HTTP 服务 + 真实文件型 SQLite：API+DB 混合 Run PASS、match_id 动态传递、令牌零明文、错误凭据 FAIL、UI 节点 BLOCKED、策略拒绝 BLOCKED、多次运行 fixture 隔离）。
- AUD-012：✅ 已交付 —— 服务端 evidence 解析 + 失败断言强制 + 脱敏 ReproductionBundle（JSON/Markdown/ZIP）+ 人工确认保留 `draft_id/approved_by` 审计；`/api/v1/aiqe/defects` 路由。测试 `tests/test_aiqe_aud012_evidence_and_draft.py`（13 条，与 AUD-016 共用）。
- AUD-013：✅ 已交付 —— `agents/protocol.py`（AgentProtocol + 全字段 AgentResult + 不变量 + BaseAgentAdapter）、`agents/registry.py`（A0–A6 编号、ALLOWED_CHILDREN、工具 allowlist、FORBIDDEN_TOOLS）、`agents/orchestrator.py`（AgentTask/AgentPlan DAG、build_plan、run_plan：WAITING_HUMAN 暂停 + 下游取消原因 + 超时 + 幂等复用 + AgentExecution 可追溯）、A0/A6 新 Agent、A4 增加 `recommended_experiment`/`missing_evidence` 必填与确定性 `confidence_band`、`AgentExecution` 扩展 14 个审计字段。测试 `tests/test_aiqe_aud013_agent_protocol.py`（16 条）。

## 5. 第三批缺口要点

- AUD-013：✅ 已交付（见第 5 节），A1/A6 已就位，A0 计划 DAG 与人工暂停可执行。剩余：把 `run_plan` 暴露为 REST/MCP 工具（`/aiqe/agent-tasks` + `aiqe.requirement.analyze` 等，见 AUD-013「追加」章节）。
- AUD-014：✅ 已交付 —— `aiqe_requirement_contracts` + `aiqe_acceptance_criteria`；按 requirement 递增 revision + `revision_checksum`；source refs（prd/figma/openapi/meeting_decision/bug/business_rule）结构化解析 + 服务端校验（`bug:` 必须存在且同项目、`ac:` 必须存在）→ `INVALID_SOURCE_REF`；状态机 DRAFT→REVIEW_REQUIRED→APPROVED→FROZEN→SUPERSEDED；P0/P1 无 Oracle 禁止批准/冻结；APPROVED/FROZEN 不可原地更新（新建 revision）；模糊词扫描（立即/实时/尽快/正常/稳定）要求指标或 SLA。
- AUD-015：✅ 已交付 —— `aiqe_test_cases`（结构化 steps/covers_ac_ids/platform_targets/oracle_ref/automation_grade A–D）；P0/P1 缺断言/Oracle/平台绑定 → D，P2/P3 → C；缺 fixture/cleanup/precondition → B；否则 A；P0/P1 必须绑定 APPROVED/FROZEN Contract revision；未知 AC 覆盖被拒绝；语义 dedupe_key 防冗余；审核门禁禁止 D 级自动执行；`coverage_report` 逐 AC 输出 UNCOVERED/PARTIAL/COVERED 并断言 P0 覆盖率。测试 `tests/test_aiqe_aud014_015_contract_testcase.py`（15 条）。
- AUD-014/015 ⇒ 已解锁 AUD-017 的强制回归集合（失败 Case + P0 Case + 合约变更覆盖 Case）。
- AUD-016：✅ 已交付 —— `evidence_service.resolve_evidence_refs` 服务端解析（存在性 + 同 Project + 同 Run，`signal:` 仅格式），任何非法引用使整个结果失败（`EVIDENCE_REF_INVALID`）；已接入缺陷草稿与 ReproductionBundle。剩余：把该解析器注入 `FailureTriageAgent.validate`（AI 归因输出校验）与 A4 调用链，属 AUD-013 任务链的一部分。
- AUD-017：✅ 已交付 —— `services/impact_service.py`：真实 `git diff`（name-status + numstat，固定 base/head SHA）、Python AST symbol、TS 导出、FastAPI route、migration 检测、确定性 component 映射；影响计划给出候选 Case 的 score/reason/**trace path**（component → AC → case）；**强制集合**由后端计算（直接失败 Case + 变更合约的 P0 Case + AC 覆盖 Case），`merge_ai_plan` 拒绝显式排除强制 Case 或不存在的 Case ID，并始终把强制集合并入最终计划；边写入既有 `ImpactEdge`（changed/covers/depends，按 version 幂等）。测试 `tests/test_aiqe_aud017_impact_graph.py`（8 条，含临时真实 git 仓库）。
- AUD-018：✅ 已交付 —— `aiqe_benchmark_datasets/samples/runs`；冻结数据集（`content_hash` + `sample_count` + `gate_eligible`，<30 只作参考）；`run_benchmark` 真实调用 Agent predictor；**后端确定性计算** micro TP/FP/FN、Precision/Recall/F1、Unknown rate（UNKNOWN 视为弃权，不计误报）、阈值状态 `PASS_GATE/BELOW_THRESHOLD/REFERENCE_ONLY`、与 baseline 对比；`learning_service.evaluate_candidate` 改为只接受 `benchmark_run_id` 并从 BenchmarkRun 派生误报率/精确率，API `EvaluateIn` 仅接受 `benchmark_run_id`（自报 payload → 422）。测试 `tests/test_aiqe_aud018_benchmark.py`（12 条）+ 重写 learning curator/API 测试。
- AUD-019：✅ 已交付 —— `aiqe_interference_observations`（detector_key/version、12 类 category、severity、±15s/10s 窗口、signal、evidence refs、建议实验；Detector 不改 Run Outcome）；`aiqe_triage_cases`（固定生命周期，禁止跳级）；`services/noise_intelligence.py`（10 个资源信号映射到 12 类 + 新增 UI_OVERLAY/CROSS_FEATURE/AUTOMATION/FLAKY/REQUIREMENT_GAP/TEST_DATA/TIME 检测器 + UNKNOWN 兜底 + 每类 E1–E6 建议 + P0 抑制守卫）；`NoiseRule` 治理（suppress 必须 reason、审批后才 active、项目作用域、续期新建版本并 supersede 旧版本、matched/false_suppress 计数）；`/admin/noise-rules/{id}/approve`。测试 `tests/test_aiqe_aud019_noise_intelligence.py`（22 条）。
- AUD-020：✅ 已交付（代码侧）—— `aiqe_platform_bindings`（AC/CASE × 9 平台 × OS/浏览器或 App 版本/设备型号/Driver 版本/节点/Profile）；`platform_binding_service` 服务端从 Capability Registry 计算 6 态（调用方不能自报 VERIFIED）、`platform_matrix` 不隐藏任何未验证平台、`preflight_platform` 对缺节点与未 VERIFIED 的真机/官方工具平台给 BLOCKED。测试 `tests/test_aiqe_aud020_platform_bindings.py`（9 条）。**遗留（环境侧）**：真实 iOS/Android/小程序设备与官方工具验收记录，需要设备实验室与真实节点，代码无法替代。

## 6. 实施顺序（本轮起的计划）

按"风险消除 / 代码量"排序，每项独立可验证：

1. ✅ AUD-001（第 1 轮）
2. ✅ AUD-004：删除伪造 verification_run_id，E1–E6 语义与单变量校验对齐 v1.5 §04（第 1 轮）
3. ✅ AUD-003：`SensitiveDataClassifier` + 输出脱敏 + Secret Handle + canary 测试（第 1 轮）
4. ✅ AUD-002：Query Registry + 项目注入 + 超时；`node_executor` 接入 db driver（第 1 轮）
5. ✅ AUD-005：capability 6 态 + Preflight（Launch 前 BLOCKED、不建空跑 Job）（第 2 轮）
6. ✅ AUD-006：fencing token + 生产事件时间线 + Reconciler（第 2 轮）
7. ✅ AUD-007：Assertion Engine + `run_assertion_results` 写入 + 断言接口（第 2 轮）
8. ✅ AUD-008：Artifact 两阶段上传/下载/RBAC/墓碑保留 + Run 证据完整性（第 3 轮）
9. ✅ AUD-009/010：部署证明 + 40 位 SHA + fingerprint 幂等 + 范围冻结；Run 终态同步 + 对比快照 + 取消（第 3 轮）
10. ✅ AUD-012/016：evidence ref 服务端解析 + 可复现缺陷草稿/复现包/人工确认（第 3 轮）
11. ✅ AUD-011：混合 Workflow Dogfood harness（真实 Driver；第 4 轮）
12. ✅ AUD-013：Agent Protocol/Registry/DAG + A0/A6 + A4 证据等级（第 4 轮）
13. ✅ AUD-014/015：Requirement Contract + 结构化 TestCase（第 5 轮）
14. ✅ AUD-019：Noise 12 类目 + Observation + Triage 生命周期 + 规则治理（第 6 轮）
15. ✅ AUD-018：Benchmark dataset/run + 后端计算指标（第 7 轮）
16. ✅ AUD-017：A5 影响图 + 强制集合不可删（第 8 轮）
17. ✅ AUD-020：PlatformBinding + 按平台 6 态 + 多端 Preflight（第 8 轮，代码侧）
18. ✅ §06 REST 契约 + AUD-013 追加 MCP 工具名（第 9 轮）

> **§06 REST 契约与 MCP 工具名（第 9 轮补充）：** 新增 `/api/v1/aiqe` 能力路由
> （contracts / cases / experiments / observations / triage / benchmarks / impact / platforms /
> agent-tasks / regression sync），全部复用已交付 service 并保持 project scope + RBAC +
> "不得自报事实"；MCP Gateway 改用规范 `aiqe.*` 工具名并标注
> READ/WRITE_DRAFT/EXECUTE_TEST/APPROVE 作用域，`close_defect` 等受保护动作永不暴露。
> 测试：`tests/test_aiqe_capabilities_api.py`（12 条）+ MCP 规范名/别名/禁列测试。
>
> **代码侧 20/20 AUD 已全部交付。** 仍未满足的是 v1.5 §00-8 的**环境证据**类完成定义：
> 真实 Test 环境下 20 次连续 Dogfood Run ID、真实 iOS/Android/小程序设备验收、Runner 出口
> 防火墙部署、24h soak 与 100 并发、以及 QA/Backend/Security/Product 四方联合签字。
> 这些需要可用的真实环境与设备，不能由代码仓库单侧完成。

> 每项完成条件遵循 v1.5 §00-8：代码 + 单测/集成测试 + 正负向/安全/权限/并发路径 + 真实 Run 证据 + OpenAPI/迁移/前端同步 + 无 secret 日志 + PR 描述含代码路径/测试命令/CI/回滚。
