# G4 独立审计报告 — V16-005 / V16-006 / V16-007（执行入口 · 租约状态机 · DAG 快照）

> **STATUS: HISTORICAL** — 本文记录 2026-11-2x 当时的执行事实与结论；其中 PASS/VERIFIED 等表述不代表当前发布判定。当前状态以 `release-verdict.json`、`E2E-Coverage-and-Blockers.md` 与 `governance/production-evidence.json` 为准。


- 审计 Issue：**V16-005（AUD-006 Worker 状态/租约/迟到结果，P1）**、**V16-006（AUD-004/009 唯一 Run Launch，P1）**、**V16-007（AUD-004/009 冻结并完整复制 DAG 快照，P1）**
- 规格：`C:\Users\26029\Downloads\CamelTv_AIQE_V1.6_修复与生产化开发实施计划.md` 第 391–419 行（V16-005）、第 421–463 行（V16-006）、第 465–492 行（V16-007）；并参照 §0.1 完成定义、§0.2.3 测试分层、§0.2.4 状态定义、§0.2.6 正/负/异常路径、§0.2.8 禁止的“通过方式”、§1 依赖顺序（第 199 行）。
- 仓库：`F:\CamelTv-worktrees\DeepSeek_Harness-aiqe-v1-6`
- 分支：`release/aiqe-v1-6`；HEAD：`86a44b2cbb7c9c44d3ef6af1e324d1f42c3eae6f`（= 规格声明的审计快照）
- 审计时间：2026-11-19T19:04:12+08:00（快照哈希见附录 A）
- 审计方式：**只读代码**。未修改任何业务文件；唯一写入为本报告。仓库外临时验证脚本只使用内存 SQLite，不写仓库、不连真实库（见附录 B）。
- 关注模块：`job_consumer` / `lease` / `reconciler` / `run_launch` / `triage_service` / `regression_service` / workflow snapshot / DAG clone / outbox / `dag_scheduler` / `execution_dispatcher` / `execution_service`（收口路径）/ `api/v1/execution_jobs.py`（外部 Runner 上报入口）

## 0. 审计口径与工作树状态（重要）

1. **工作树有在途改动（V16-001），本报告基于审计时刻的工作树快照，而非 HEAD 提交内容。**
   `git status --porcelain` 在审计时刻有 18 项已修改 + 3 项未跟踪，其中 `app/aiqe/services/run_launch.py`（11237→11671 字节，`+6` 行 `NEEDS_POLICY_REVIEW` 闸门）、`app/aiqe/services/execution_service.py`、`app/api/v1/execution_jobs.py` 属于 V16-001 的在途改动；`run_launch.py` 在本审计过程中被并行修改过（行号整体 +6），本报告行号一律按附录 A 的 SHA256 对齐。
2. **判定只以代码行证据为准。** 不凭类名/文件名/文档声明判定；文档声明与实测冲突处按规格 §0.2.8 计为“未实现”，并在 §5.1 单列。
3. **“已存在的基础设施”与“本 Issue 的交付物”严格区分。** V16-005/006/007 的多数组件是 v1.4 / V1.5（PR #618、PR #595）遗留，不是 V1.6 交付；本报告只判定规格定义的 V1.6 目标行为，并对“遗留设施能证明什么、不能证明什么”逐条标注。
4. **实测证据**取自三份内存 SQLite 验证脚本（附录 B），用于证明“QUEUED 无 Job”“Reconciler 漏收口”“CLI 崩溃”“token 缺省即放行”“终态可回退”“克隆丢边/丢断言”等事实。脚本不改仓库文件。
5. **本轮不评估前端**：`git grep -in "experiment\|regression" -- test-platform-v2/frontend/src` 对 AIQE `experiments` / `defects/{id}/regressions` 端点 **0 命中**（仅命中 release-bundles 与 theme registry），即 V16-006 涉及的 triage/regression 入口在仓库内没有 UI 消费者，“正式入口”就是 REST API 本身。

## 1. 总体结论

| Issue | 状态 | 一句话结论 |
|---|---|---|
| **V16-005** | **PARTIAL** | 租约/fencing 的**数据与工具**存在（`node_runs.fencing_token`、原子 claim、Reconciler requeue/BLOCKED、事件幂等），但**没有任何一条正式写结果路径强制校验 token 或租约**：进程内执行链 `complete_node()` 不传 token，外部 Runner 上报 API 也不传 token；规格要求的条件更新+rowcount、Job 幂等唯一键、QUEUED 无 Job 回收、Job 成功但 Node 未收口、证据不足不得 PASS、7 个审计事件名全部缺失；运维对账 CLI 在成功路径直接 `TypeError`。 |
| **V16-006** | **MISSING** | 规格的 `launch_run(project_id, workflow_snapshot_id, execution_kind, idempotency_key, …) -> LaunchResult` **契约字段全仓 0 命中**（`workflow_snapshot_id` / `execution_kind` / `LaunchResult`）；`triage_service` 与 `regression_service` **未改造**，仍各自 `TestRun(status="QUEUED")` 后 `create_node_runs()` 结束。实测：实验与回归各创建了 1 条 QUEUED Run、**ExecutionJob = 0**、Reconciler 扫描 0 条，Run 永久停留 QUEUED。 |
| **V16-007** | **MISSING** | 无 `WorkflowSnapshot` 不可变记录（模型/表/迁移 **0 命中**）、无 `SnapshotCloner`；两处克隆手写 graph 且硬编码 `depends_on: []` + `edges: []`，并丢弃 assertions/outputs/type/capability/resource_keys。实测：`login→verify` 基线图克隆后无依赖，克隆 Run 的 `workflow_checksum=''`、`workflow_snapshot_json={}`。 |

> **为什么 V16-006/007 不是 PARTIAL**：`run_launch.py` 是 v1.4 FIX-006 遗留的手动 Run 入口，其签名、返回值、事务边界均不符合 V16-006 目标契约，且规格点名的两个调用方（triage/regression）逐字未改；V16-007 要求的“不可变快照 + 官方 cloner + canonical hash + clone diff”在仓库内连雏形都不存在（grep 0 命中）。**为什么 V16-005 是 PARTIAL 而不是 MISSING**：fencing token 列/迁移、原子认领、租约回收、事件幂等这些“可被复用的机制”确有代码并已在 `test_aiqe_aud006_state_recovery.py` 中跑通（83 个相关用例全绿），只是**没有接到正式写路径上**，属于“机制在、验收不成立”。

### 1.1 V16-005 分项状态（规格 §V16-005 逐条）

| 规格项 | 状态 | 依据 |
|---|---|---|
| 统一状态约束：Run `CREATED→PREFLIGHT→QUEUED→RUNNING→{PASSED,FAILED,BLOCKED,CANCELLED,ERROR}` | **不符合且无差异说明** | 实际 Run 状态集为 `DRAFT/VALIDATING/QUEUED/RUNNING/WAITING_HUMAN/TRIAGING/COMPLETED/BLOCKED/CANCELED/ERROR` + `outcome`（`app/aiqe/services/run_state.py:21-51`），无 `CREATED/PREFLIGHT/PASSED/FAILED`（G4-005-13） |
| 统一状态约束：Job `PENDING→CLAIMED→RUNNING→{SUCCEEDED,FAILED,RETRY_WAIT,CANCELLED,DEAD}` | **不符合且无差异说明** | 实际 Job 状态为 `pending/running/success/failed/canceled/expired`（`job_consumer.py:69,167`、`execution_service.py:802`、`reconciler.py:198,222`、`run_launch.py:311-312`）；无 `CLAIMED/SUCCEEDED/RETRY_WAIT/DEAD`（G4-005-13） |
| 终态不可回退；重跑必须是新 Attempt | **不符合** | `dag_scheduler.complete_node()` 无终态守卫、无条件写 `row.status = status`（`dag_scheduler.py:404`）；实测 PASSED 节点被迟到 FAILED 覆盖（附录 B·F） |
| `QUEUED` 必须对应 pending Job 或 QueueTicket，否则限时转 BLOCKED/ERROR | **不符合** | Reconciler 只 select `TestRun.status == "RUNNING"`（`reconciler.py:153`）；实测 QUEUED Run（无 Job）对账后仍 QUEUED、`runs_scanned=0`（附录 B·C） |
| 实施 1：claim 产生单调递增 fencing token，Worker 每次写结果携带 token | **PARTIAL（仅 token 生成）** | claim 递增 `node_runs.fencing_token`（`job_consumer.py:80-92`）；但正式写结果路径不带 token（`execution_service.py:486-494`、`api/v1/execution_jobs.py:202-211`） |
| 实施 2：条件更新 `WHERE job_id AND lease_owner AND fencing_token AND status IN (...)`；rowcount=0 丢弃 | **MISSING** | 全仓无该更新语句；写结果走 ORM 赋值后 commit（`dag_scheduler.py:404`、`execution_service.py:802-820`） |
| 实施 3：Job 幂等键 `(run_id,node_run_id,attempt_no,execution_kind)` 唯一约束 | **MISSING** | `execution_jobs` 无这 4 列（`app/models/execution_job.py:22-45`；`alembic/versions/20260923_batch258_execution_jobs.py:29-51`）；`run_launch.py:6` 的“DB 唯一约束”声明与事实相反（见 G4-005-03） |
| 实施 4：外部动作 idempotency key；不支持的声明 at-least-once | **PARTIAL** | `httpx_driver.py:169-182` 支持 `idempotency_key` 重试；validator 对写操作 `max_attempts>1` 强制 `idempotency_key_expr`/`compensation_node`（`workflow_validator.py:161-167`）；但**没有**“at-least-once 风险声明/补偿策略”字段或校验 |
| 实施 5：Reconciler 处理过期 lease / 无 Job 的 QUEUED Run / Job 完成但 Node 未收口 / Node 终态但 Run 未收口 / 重复事件 / Artifact 悬挂 | **PARTIAL** | 已覆盖：过期 lease（`reconciler.py:220-262`）、Job 丢失（`:176-190`）、Job failed/canceled（`:197-219`）、长期 pending（`:263-280`）、Node 全终态→Run 收口（`:78-98`）、重复事件（`event_service.py:75-83` + `uq_run_events_run_producer_event`）；**未覆盖**：QUEUED 无 Job、Job 成功但 Node 未收口、Artifact 悬挂/不完整（实测 H/I） |
| 实施 6：不得凭猜测把 RUNNING 标 PASSED；证据不足标 ERROR/UNKNOWN | **不符合** | `reconciler._finalize_run` 不看 Assertion/Artifact（`reconciler.py:78-98`）；实测 artifact `PENDING_UPLOAD` 时 Reconciler 给 `COMPLETED/PASS`，同一事实经 `dag_scheduler.finalize_run` 给 `COMPLETED/INCOMPLETE`（附录 B·I/I2） |
| 实施 7：审计事件 `JOB_CLAIMED/LEASE_RENEWED/LEASE_EXPIRED/FENCING_REJECTED/JOB_RETRIED/NODE_FINALIZED/RUN_FINALIZED` | **MISSING** | 7 个事件名全仓 0 命中（§6 命令 4）；实际用 `job.dispatched`/`node.ready`/`node.lease_expired`/`node.reconciled`/`run.completed`/`run.reconciled`；重放拒绝**不写任何事件**（`job_consumer.py:126-135`） |

### 1.2 V16-006 分项状态

| 规格项 | 状态 | 依据 |
|---|---|---|
| 目标接口 `launch_run(db, *, project_id, workflow_snapshot_id, execution_kind, idempotency_key, requested_scope, source_run_id, defect_id, experiment_id, requested_by) -> LaunchResult` | **MISSING** | 实际 `launch_run(db, *, project_id, user_id, workflow_definition_id, graph_override, expected_checksum, retest_of, environment_id, build_ref, commit_sha, run_key, launch_key, source_type, source_id, execution_profile_id, environment_snapshot) -> TestRun`（`run_launch.py:86-104`）；`workflow_snapshot_id`/`execution_kind`/`LaunchResult` 0 命中 |
| `LaunchResult` 字段 `run_id/run_status/job_ids/node_run_ids/snapshot_hash/dispatch_status/blocked_reason` | **MISSING** | 返回 ORM `TestRun`；API 只回 `{run, preflight, node_count}`（`api/v1/aiqe_runs.py:83-89`） |
| Run/NodeRun/ExecutionJob/Outbox 同事务持久化，发布走 Outbox relay | **PARTIAL** | Run+NodeRun+Job 同事务（`run_launch.py:212-284`）；Job 无 outbox（`execution_dispatcher.py:82-94` 直接 `db.add`）；`event_outbox` 只服务 SSE，`dispatch_outbox` 无调用方（G4-006-06） |
| 步骤 1：`run_launch.py` 成为唯一正式 Run 创建服务；triage/regression 禁止自行 QUEUED | **不符合** | 4 个非 launch 创建点：`triage_service.py:231-247`、`regression_service.py:344-376`、`dogfood.py:370-379`、`scripts/qa/aiqe_bootstrap_run.py:83-98` |
| 步骤 2：只接受冻结快照，不接受未校验临时 graph | **PARTIAL** | `graph_override` 分支（`run_launch.py:105-116`）仍接受任意 graph，但**无生产调用方**；workflow 分支有 checksum 校验（`:121-130`） |
| 步骤 3：Preflight 校验 Project/Environment/Policy/Driver/Capability/Secrets/Query Registry/mandatory scope | **PARTIAL（5/8）** | 有 Environment/Profile/Capability/Secret/Fixture（`preflight.py:113-257`）+ Driver 注册（`workflow_validator.py:146-150`）；**无** TargetPolicy、Query Registry、mandatory scope |
| 步骤 4：初始化 DAG 节点/边/依赖与 Job；无 READY 节点、环路、缺依赖、无可执行范围均拒绝 | **PARTIAL** | 环路/缺依赖/边一致性有（`workflow_validator.py:186-207`）；`run_launch` 路径会派发 Job；但“无 READY 节点/无可执行范围”不拒绝——`schedule()` 找不到可运行节点时直接返回，Run 仍被置 RUNNING（`run_launch.py:291-292`） |
| 步骤 5：Outbox Pattern（同事务写 Outbox，relay 至队列，消费者幂等 claim） | **MISSING（发布侧）** | 无 job outbox/relay；`dispatch_outbox` 只把 `dispatched_at` 置位（`event_service.py:123-139`）且无调用方 |
| 步骤 6：API 响应区分 `ACCEPTED/QUEUED` 与 `RUNNING`；只有 Worker claim 后才 RUNNING | **不符合** | `launch_run` 内 `schedule()` 立即把 QUEUED 推成 RUNNING（`dag_scheduler.py:258-259`），返回前又兜底 `QUEUED→RUNNING`（`run_launch.py:291-292`）；测试也把 `run.status == "RUNNING"` 固化为契约（`test_aiqe_run_launch.py:172`） |
| 步骤 7：返回 QUEUED 时必须有 `job_ids` 或资源等待记录 | **不符合** | 返回值无 job_ids；只有 `job.dispatched` 事件里带单个 job_id（`run_launch.py:269-281`） |
| 步骤 8：所有执行类型共用同一 Finalizer/Assertion/Artifact/Outcome | **不符合（对 triage/regression）** | 实验/回归 Run 无 Job，从不进入 `finalize_node()`；其终态只能靠测试手工赋值（`test_aiqe_regression_api.py:223-249`）或永不发生 |

### 1.3 V16-007 分项状态

| 规格项 | 状态 | 依据 |
|---|---|---|
| 快照冻结内容：Workflow ID/version、Case IDs、Node spec/type、Driver/adapter version | **MISSING** | 仅 `TestRun.workflow_snapshot_json` 内联 graph（`models/run.py:59`）；无 driver/adapter 版本、无 case ids、无独立 ID |
| `depends_on`、edges、条件边、分支规则、循环限制、timeout/retry policy | **MISSING（克隆路径）** | 克隆硬编码 `depends_on: []`/`edges: []`（`triage_service.py:262,266`；`regression_service.py:221,225`）；timeout/retry 完全不复制 |
| 输入参数 schema、RunContext binding、输出映射、Secret Handle 策略 | **MISSING（克隆路径）** | 克隆只带 `input`；`outputs`/`output_schema`/`secret_keys`/`resource_keys` 不复制 |
| Assertions/Oracle、mandatory scope、环境绑定、TargetPolicy hash、Query Registry version | **MISSING（克隆路径）** | 克隆不带 `assertions`；实测克隆节点 `assertions_json=[]`（附录 B·A）。环境绑定只部分随 `environment_snapshot_json` 复制 |
| Agent/Prompt/Tool version（Agent 生成 workflow） | **未涉及** | 仓库无 Agent 生成 workflow 的 Run 路径；不构成本 Issue 的 gap（记为 N/A） |
| 步骤 1：新建不可变 `WorkflowSnapshot`（canonical JSON + schema version + sha256 + source revision） | **MISSING** | 全仓 `WorkflowSnapshot` 0 命中；`alembic/versions` 无相关迁移；无 checksum 列以外任何快照元数据 |
| 步骤 2：Run 只能绑一个不可变快照；运行中禁止改 graph | **PARTIAL** | 有 run 级内联副本 + `workflow_checksum`（`models/run.py:58-59`、`run_launch.py:218-219`），但 JSON 列可写、无不可变约束/触发器；`WorkflowDefinition` 审批后冻结（`workflow_service.py:69-81`）只保护源定义，不保护 Run 内联快照 |
| 步骤 3：`SnapshotCloner` 复制并验证 DAG；禁止手写 NodeRun 复制 | **MISSING** | `SnapshotCloner` 0 命中；两处手写（`triage_service.py:249-268`、`regression_service.py:207-227`） |
| 步骤 4：保留 edges/depends_on/conditions；节点 ID 映射后重写 edge endpoints | **不符合** | 克隆只保留 node key（无新 ID），边与依赖被丢弃（见上） |
| 步骤 5：snapshot schema 升级用显式 migrator；不支持版本标 BLOCKED | **MISSING** | `schema_version` 只存在于 `WorkflowDefinition`（`models/workflow.py:38`，自由字符串）；Run 侧无版本字段，无 migrator，无 BLOCKED 分支 |
| 步骤 6：生成 clone diff，记录被排除节点及原因；不得让依赖被排除后静默变无依赖 | **MISSING** | 回归只有 **case 级** `excluded_json`（`regression_service.py:166-179,330`）；无节点级 diff；克隆后所有节点恒为“无依赖”，正是规格禁止的静默降级 |
| 验收：8 节点、分支、并行、汇合、动态输出 DAG 的 clone hash 一致 | **无测试** | 现有克隆测试基线图无 edges（`test_aiqe_triage_experiments.py:27-34`）、回归源 Run 仅 1 节点（`test_aiqe_regression_api.py:78-106`） |
| 验收：拓扑排序/边数/入度出度/条件边一致 | **无实现、无测试** | 克隆结果 edges=[]，恒等于不一致 |
| 验收：缺父节点、循环、未知引用必须拒绝 | **PARTIAL** | `validate_workflow()` 能拒绝（`workflow_validator.py:132-207`），但只在 `launch_run` 调用；克隆路径直接 `dag_scheduler.create_node_runs()`（`dag_scheduler.py:112-134`）不做任何校验 |

## 2. V16-005 详审：Worker Lease / Fencing / Reconciler

### 2.1 现有机制到底做到了什么（可复用部分，避免误判为全缺）

| 机制 | 代码 | 实测/测试 | 能证明什么 | 不能证明什么 |
|---|---|---|---|---|
| 原子认领（条件 UPDATE + rowcount） | `job_consumer.py:42-94`（`:65-78` 条件更新 `status='pending'`，`:78` 检查 rowcount） | `test_aiqe_executor_consumer.py:120-131` | 单进程内重复 claim 不会二次认领 | 跨进程/多 Worker 并发（SQLite 无行锁；`test_*` 未覆盖并发） |
| fencing token 列 | `models/run.py:133`（NodeRun）、`:164`（StepAttempt）；迁移 `20261124_aud006_fencing_token.py:19-32` | `test_aiqe_aud006_state_recovery.py:75-79`（claim 后 token=1） | token 会被 claim 提升 | token 被写入结果方消费（见 2.2） |
| 租约字段 | `models/execution_job.py:34-40`；claim 写 `lease_expires_at`（`job_consumer.py:75`）、心跳续租（`api/v1/execution_jobs.py:167-178` → `execution_job_service.heartbeat:202-216`） | `test_aiqe_aud006_state_recovery.py:117-123` | 租约记录存在 | 过期租约能拒绝写入（`assert_writable` 不校验过期，见 G4-005-08） |
| Reconciler 过期租约处理 | `reconciler.py:220-262`（超 3 次 → BLOCKED；否则 PENDING + 提升 token） | `test_aiqe_aud006_state_recovery.py:146-198`、`test_aiqe_reconciler.py:44-59` | 过期 Job 会被收口/重排 | 重排后旧 Worker 的写入会被拒（生产路径无 token，见 2.2） |
| 过期租约回收（控制面） | `execution_job_service.reclaim_stale:145-166`（running→pending） | `test_execution_job_report.py`（另域） | 断线任务能回 pending | 回收后 fencing 单调性（reclaim 不碰 node token） |
| 事件幂等 | `event_service.py:75-83` + DB 唯一约束 `(run_id, producer_event_id)`（`alembic/versions/20261112_ta006_run_events.py:64-66`） | `test_aiqe_aud006_state_recovery.py:268-287` | 重复事件不重复入库 | 重复**消息**（Job 投递）幂等（G4-005-03） |

### 2.2 关键证据（fail-open 主链）

1. **进程内 Worker 写结果完全不校验 token/租约。**
   `execution_service.execute_inprocess_job()` 只在入口检查 `job.status == "running"`（`execution_service.py:667-673`），随后直接 `execute_node()`（`:776-782`）→ `finalize_node()`（`:792-801`）→ `dag_scheduler.complete_node(..., 无 fencing_token)`（`execution_service.py:486-494`）。`complete_node()` 里 token 校验是**可选**的（`dag_scheduler.py:399-403`：`if fencing_token is not None`），因此该链路 100% 跳过校验。
2. **外部 Runner 上报 API 也不传 token。**
   `POST /api/v1/execution-jobs/{job_id}/report` → `complete_from_report(db, job_id=..., status=..., result=..., error_message=...)`（`api/v1/execution_jobs.py:202-211`），**没有** `fencing_token` 参数；`complete_from_report` 的校验条件是 `if fencing_token is not None`（`job_consumer.py:114`）。实测：同一过期节点，`fencing_token=2` 返回 `STALE_LEASE`，`fencing_token=None` 直接放行并调用 `complete_from_external_report`（附录 B·E）。
3. **租约过期在写路径永不触发。**
   `lease.assert_writable()` 不接收 `job_expires_at`（`lease.py:101-105`），全仓唯一传 `job_expires_at` 的调用方是测试 `test_aiqe_aud006_state_recovery.py:134-142`；`LeaseExpired` 在生产链路是死代码。
4. **终态可回退。**
   `dag_scheduler.complete_node()` 无 `row.status in NODE_TERMINAL` 守卫，直接 `row.status = status`（`dag_scheduler.py:404`）。实测 PASSED→FAILED 覆盖成功（附录 B·F），违反“终态不可回退”。
5. **StepAttempt token 恒 0。**
   `StepAttempt(...)` 三处构造（`dag_scheduler.py:95-100`、`:366-374`、`execution_service.py:371-377`）都不传 `fencing_token`；`grep "fencing_token\s*="` 在 `app/aiqe/services` 只命中 `lease.py`/`resource_lock.py`。因此 `test_attempt_records_fencing_token`（`test_aiqe_aud006_state_recovery.py:290-304`）的 `>= 0` 断言恒真——**该用例无证明力**。
6. **Reconciler 漏两类状态。**
   - 无 Job 的 QUEUED Run：只扫 RUNNING（`reconciler.py:150-157`）；实测 `runs_scanned=0`（附录 B·C）。
   - Job 已完成但 Node 未收口：分支只有 job missing / failed / canceled / running+expired / pending（`reconciler.py:176-197,220,263`），**没有 `success` 分支**；实测 job=success + node=RUNNING 对账后仍 RUNNING（附录 B·H）。
7. **Reconciler 可凭节点状态给 PASS，绕过证据完整性。**
   `_finalize_run` 只判断“全部终态 + 有无 FAILED/BLOCKED”（`reconciler.py:78-98`），不调用 `artifact_service.incompleteness_reasons`（该检查只存在于 `dag_scheduler._finalize:207-214`）。实测：同一份 `PENDING_UPLOAD` Artifact，Reconciler 给 `COMPLETED/PASS`，`dag_scheduler.finalize_run` 给 `COMPLETED/INCOMPLETE`（附录 B·I/I2）。
8. **Reconciler 吞异常。**
   `except (LookupError, Exception): pass`（`reconciler.py:233-234`）：`bump_fencing_token` 失败的窗口被静默吞掉，正好是“租约已回收但旧 token 未失效”的 fail-open 方向。
9. **恢复路径可能复用旧 Job。**
   `dag_scheduler.recover()` 把 RUNNING 改 PENDING，但不清 `execution_job_id`、不提升 token（`dag_scheduler.py:476-504`）；随后 `enqueue_node_run()` 遇到仍为 `pending/running` 的旧 Job 会原样返回（`execution_dispatcher.py:59-63`），等于把旧 Job 再派一次。
10. **运维入口不可用。**
    `scripts/qa/aiqe_reconcile.py:30-32` 成功路径执行 `json.dumps({"ok": True, **stats})`，而 `stats` 是 `ReconcileReport` dataclass（`reconciler.py:101-136` 只有 `payload()/__getitem__/get`，无 `keys()`）→ `TypeError: 'ReconcileReport' object is not a mapping`（实测，附录 B·D），退出码 2。`docs/aiqe/ops.md:69` 明确把该命令作为“必须定时”的对账入口。
11. **默认部署没有 Reconciler/Consumer。**
    `aiqe_inprocess_executor_enabled=False`、`aiqe_reconciler_enabled=False`（`config.py:26-34`），只在 lifespan 显式开启时启动（`main.py:172-186`）；`git grep -i "AIQE_" -- deploy` **0 命中**，仓库内没有任何部署清单设置这两个开关。

### 2.3 V16-005 gaps（可逐条复核）

- **G4-005-01（P0，fail-open）** 写结果路径无 fencing 强校验：`execution_service.py:486-494`、`api/v1/execution_jobs.py:202-211`、`job_consumer.py:114`。复核：`python -c` 脚本 E；或 `git grep -n "complete_from_report(" -- test-platform-v2/backend/app` 只有 API 一处且无 token 参数。
- **G4-005-02（P0）** 无“条件更新 + rowcount=0 丢弃”实现；`dag_scheduler.py:404` 无条件回写；终态可回退（实测 F）。
- **G4-005-03（P0）** Job 幂等唯一键缺失：`(run_id,node_run_id,attempt_no,execution_kind)` 4 列均不存在（`app/models/execution_job.py:22-45`、`alembic/versions/20260923_batch258_execution_jobs.py:29-51`）；`run_launch.py:6` 的“DB 唯一约束”是错误声明；`models/run.py:143` 的唯一约束方向相反（限制一个 Job 不能挂两个 Node）。
- **G4-005-04（P1）** `QUEUED` 无 Job 不回收：`reconciler.py:153`；实测 C。且该状态正是 triage/regression 制造的（见 V16-006）。
- **G4-005-05（P1）** “Job 成功但 Node 未收口”无分支：`reconciler.py:176-197,220,263`；实测 H。
- **G4-005-06（P0）** Reconciler 可给 PASS 而不校验 Artifact/Assertion：`reconciler.py:78-98`；实测 I/I2 与 `dag_scheduler.py:207-214` 行为分叉。
- **G4-005-07（P1）** 7 个规格审计事件名缺失，`FENCING_REJECTED` 等拒绝路径不落事件：`job_consumer.py:126-135`、`dag_scheduler.py:399-403`（§6 命令 4）。
- **G4-005-08（P1）** `assert_writable` 不校验租约过期，`LeaseExpired` 在生产链路不可达：`lease.py:95-105`。
- **G4-005-09（P2）** `StepAttempt.fencing_token` 从不赋值，相关测试断言恒真：`dag_scheduler.py:95-100,366-374`、`test_aiqe_aud006_state_recovery.py:290-304`。
- **G4-005-10（P1）** `recover()` 不清 `execution_job_id`/不提升 token，可能复用旧 Job：`dag_scheduler.py:476-504` + `execution_dispatcher.py:59-63`。
- **G4-005-11（P1，运维）** 对账 CLI 成功路径崩溃：`scripts/qa/aiqe_reconcile.py:30-32`（实测 D）；无测试覆盖该入口；`docs/aiqe/ops.md:67-71` 的“必须定时”承诺失效。
- **G4-005-12（P1）** 状态名与规格不一致且无差异说明/ADR：`run_state.py:21-51`、`job_consumer.py:69/167`、`dag_scheduler.py:23`（`CANCELED` 与规格 `CANCELLED` 不一致）；规格第 11 行要求“先提交差异说明和 ADR”。
- **G4-005-13（P2）** 默认部署无运行时：`config.py:26-34`、`main.py:172-186`、`deploy/` 无 `AIQE_*`。
- **G4-005-14（P1）** 验收测试矩阵缺失（Worker 四种崩溃点、重复投递 2/10/100、租约竞争、Reconciler ×10 幂等），见 §2.4。

### 2.4 V16-005 已存在测试及入口质量

| 测试文件 | 入口 | 覆盖 | 入口质量判定 |
|---|---|---|---|
| `tests/test_aiqe_aud006_state_recovery.py`（337 行，15 例） | 直调 `job_consumer.claim_aiqe_jobs` / `run_job` / `reconcile` / `lease.assert_current` / `dag_scheduler.complete_node` | token 提升、旧 token 拒绝、租约字段、过期租约重排/上限 BLOCKED、Run 收口、事件幂等、重复事件、外部 stale report | **部分合格**：`run_job` 是正式 Worker 入口；但 `_seed_run`（`:41-57`）**自行构造 `TestRun(status="QUEUED")` 并直调 `dag_scheduler.schedule`**，绕过 Run Launch；`assert_current`/`complete_node` 是 helper 级；`test_attempt_records_fencing_token:290-304` 断言恒真；无 token=None 用例、无崩溃/重复投递/并发用例 |
| `tests/test_aiqe_reconciler.py`（118 行，6 例） | 直调 `reconcile()`，数据由 `_seed`（`:11-41`）手工插入 TestRun/NodeRun/ExecutionJob | 过期租约重排、failed job 收口、pending 超时 BLOCKED、全终态收口、COMPLETED 无 outcome、无节点 Run | **不合格**：全部手工造行 + 直调服务函数；无 QUEUED 无 Job、无 job-success、无 artifact 用例；未覆盖 CLI |
| `tests/test_aiqe_executor_consumer.py`（152 行，5 例） | `job_consumer.claim_aiqe_jobs` + `run_job` | http 节点 PASSED/FAILED、claim 幂等（两次）、非 AIQE Job 不认领、无能力 driver BLOCKED | **部分合格**：Worker 入口真实；但 `_seed_run`（`:43-54`）直接建 QUEUED Run + schedule，绕过 Launch；`monkeypatch` 替换 `SafeHttpExecutor.request`（对 V16-005 可接受，因为不验证网络）；`test_claim_is_idempotent` 仅证明“第二次 claim 返回空”，不是重复消息 2/10/100 |
| `tests/test_aiqe_dag_scheduler.py`（143 行，6 例） | 直调 `dag_scheduler.schedule/complete_node/recover` | 串并/汇合/失败阻断/资源锁/恢复/client cleanup | **不合格（对本 Issue）**：纯 helper 级；`test_recover_resumes_running_node:110-121` 未断言 `execution_job_id`/token，掩盖 G4-005-10 |

**结论（V16-005 测试）**：规格 §0.2.6 要求的“重复消息、超时、Worker 崩溃、竞态”一条都没有；§0.2.3 要求的“从正式入口进入”只有 `test_aiqe_executor_consumer.py` 部分满足；规格列出的 5 条验收（执行前/执行中/写结果前/写结果后崩溃、2/10/100 重复投递、A 过期 B 高 token 拒绝 A 迟到结果、Reconciler ×10 幂等、QUEUED 无 Job SLA 转 ERROR/BLOCKED）中 **0 条**被完整覆盖（第 3 条只有 helper 级替代物，且生产路径不传 token）。

## 3. V16-006 详审：唯一 Run Launch

### 3.1 关键证据（正式入口实测）

1. **契约字段不存在。** `git grep -n "workflow_snapshot_id\|execution_kind\|LaunchResult" -- test-platform-v2/backend/app` → 0 命中；实际签名见 `run_launch.py:86-104`。
2. **实验验证 Run 无 Job（API 正式入口）。**
   `POST /api/v1/aiqe/experiments/{id}/launch`（`api/v1/aiqe_triage.py:69-83`）→ `triage_service.launch_experiment`（`:272-318`）→ 默认 launcher `default_run_launcher`（`:222-269`）：
   - `run = TestRun(..., status="QUEUED")`（`:231-245`）——**不经过 `launch_run`**；
   - `dag_scheduler.create_node_runs(...)`（`:268`）——**不创建 ExecutionJob**；
   - 实测：`verification_run.status=QUEUED`、`ExecutionJob count=0`、`workflow_checksum=''`、`workflow_snapshot_json={}`（附录 B·A）。
   - `launch_experiment` 还**不做项目作用域校验**（`:279-299` 只比较 baseline 与 experiment 的 project），属跨域风险（见 §5.3）。
3. **回归验证 Run 无 Job。**
   `POST /api/v1/aiqe/defects/{id}/regressions`（`api/v1/aiqe_regressions.py:94-128`）→ `create_regression_request`（`regression_service.py:230-398`）：
   - `TestRun(..., status="QUEUED")`（`:344-372`）——**不经过 `launch_run`**、无 preflight、无 `workflow_snapshot_json`；
   - `_replicate_nodes()`（`:204-227`）只 `create_node_runs`，**无 Job**；
   - 实测：`regression_run.status=QUEUED`、`ExecutionJob count=0`、`workflow_checksum=''`（附录 B·B）。
4. **QUEUED 无 Job 无人兜底。** Reconciler 只扫 RUNNING（`reconciler.py:153`）；实测两条 Run 在对账后仍 QUEUED、`runs_scanned=0`（附录 B·C）。实验状态同步 `sync_experiment_result` 也只会一直返回 QUEUED（`triage_service.py:340-343`）。
5. **API 无法回答“有没有 Job”。** `POST /api/v1/aiqe/runs` 只返回 `{run, preflight, node_count}`（`api/v1/aiqe_runs.py:83-89`）；`GET /aiqe/runs/{id}/nodes` 也不返回 job_id（`api/v1/aiqe_runs.py:276-326`）。规格“Launch 返回 QUEUED 时必须有 job_ids”不成立。
6. **Run 在 Launch 内就被置 RUNNING。** `dag_scheduler.schedule()` 遇 QUEUED 立即 `apply_transition(run, "RUNNING")`（`dag_scheduler.py:258-259`），`run_launch` 返回前再兜底一次（`run_launch.py:291-292`）；测试把该行为固化为断言（`test_aiqe_run_launch.py:172` 期望 `RUNNING`）。规格“只有 Worker 真正 claim 后才 RUNNING”不成立。
7. **无 Outbox relay。** Job 就是 `execution_jobs` 表行（`execution_dispatcher.py:82-94`）；`event_outbox` 只给 SSE；`dispatch_outbox`（`event_service.py:123-139`）只是把 `dispatched_at` 置位、**无任何调用方**；`consume_terminal_events`（`regression_terminal.py:285-309`）同样**无调用方**（§6 命令 5）。因此“relay 崩溃/重复发布/队列不可用可恢复”既无实现也无测试。
8. **Preflight 缺 3 项。** `preflight.py:113-257` 不含 TargetPolicy、Query Registry、mandatory scope；`run_launch` 也不在 preflight 前解析策略。
9. **幂等语义分散。** `launch_key` 可选（`run_launch.py:195-202`）；triage 幂等在 `triage_experiments.idempotency_key`（`models/triage.py:48`，迁移唯一约束），regression 幂等在 `DefectRegression.idempotency_fingerprint`（`regression_service.py:302-313`）；三者不是同一个键空间，规格“重复请求相同幂等键返回同一 Run，不创建第二个 Job”无法统一断言。
10. **其它创建点。** `dogfood.py:370-379`、`scripts/qa/aiqe_bootstrap_run.py:83-98` 也是直接建 Run（前者为运维 smoke，后者为 CLI 引导），证明“唯一 Launch”未成立。

### 3.2 V16-006 gaps

- **G4-006-01（P0）** 目标契约缺失：`workflow_snapshot_id`/`execution_kind`/`idempotency_key`/`requested_by`/`LaunchResult` 全仓 0 命中；`run_launch.py:86-104` 仍是 v1.4 签名。
- **G4-006-02（P0）** triage 自行创建 QUEUED Run 且无 Job：`triage_service.py:222-269`（`:244` 状态、`:268` 只建 NodeRun）；API 入口 `api/v1/aiqe_triage.py:69-83`。
- **G4-006-03（P0）** regression 自行创建 QUEUED Run 且无 Job：`regression_service.py:344-376`；API 入口 `api/v1/aiqe_regressions.py:94-128`。
- **G4-006-04（P1）** QUEUED 无 Job 不转 BLOCKED/ERROR：`reconciler.py:153`；实测 C。
- **G4-006-05（P1）** 响应/返回值不含 `job_ids/node_run_ids/snapshot_hash/dispatch_status/blocked_reason`：`api/v1/aiqe_runs.py:83-89`、`run_launch.py:294`。
- **G4-006-06（P1）** 无 job outbox/relay；`dispatch_outbox`/`consume_terminal_events` 无调用方（`event_service.py:123-139`、`regression_terminal.py:285-309`）。
- **G4-006-07（P1）** Launch 即 RUNNING：`dag_scheduler.py:258-259`、`run_launch.py:291-292`；测试固化为契约（`test_aiqe_run_launch.py:172`）。
- **G4-006-08（P1）** Preflight 缺 Policy/Query Registry/mandatory scope：`preflight.py:113-257`。
- **G4-006-09（P2）** 执行类型未建模（只有自由字符串 `source_type`）：`run_launch.py:215`、`triage_service.py:234`、`regression_service.py:347`。
- **G4-006-10（P2）** 其它绕过点：`dogfood.py:370-379`、`scripts/qa/aiqe_bootstrap_run.py:83-98`。
- **G4-006-11（P2）** `graph_override` 分支跳过审批/策略门（`run_launch.py:105-116`），当前无调用方，属“未校验临时 graph”的潜在入口。
- **G4-006-12（P1）** 验收不可达：E1–E6 无 `job_id`、Run 上无 snapshot hash、实验/回归 Run 无终态（实测 A/B/C）。

### 3.3 V16-006 已存在测试及入口质量

| 测试文件 | 入口 | 覆盖 | 入口质量判定 |
|---|---|---|---|
| `tests/test_aiqe_run_launch.py`（402 行，17 例） | **直调 `launch_run()`**（服务层，非 HTTP） | 未审批/checksum/生产开关/环境缺失拒绝；创建节点 + Job + 事件；`launch_key` 幂等；secret 不入库；cancel | **部分合格**：覆盖了拒绝路径与 Job 创建，但**无一条经 `POST /api/v1/aiqe/runs`**；`test_launch_creates_nodes_and_dispatches_job:172` 断言“launch 后即 RUNNING”；`test_launch_key_is_idempotent:185-211` 只证明同 key 不重复建 Run/Job，未覆盖“并发同 key”与 outbox relay 崩溃 |
| `tests/test_aiqe_triage_experiments.py`（331 行，15 个测试函数，其中 1 个为 6 参数化用例） | **直调** `create_experiment/launch_experiment/sync_experiment_result` | 单变量校验、baseline 必须真实、状态 VALIDATED、幂等、launch 生成真实 Run、多变量 BLOCKED、终态同步、UNKNOWN | **不合格（对本 Issue）**：全文 **0 次**引用 `ExecutionJob`；`:165` 明确断言 `run.status == "QUEUED"`，把“QUEUED 无 Job”固化为正确行为；基线图无 edges（`:27-34`），无法发现 DAG 丢失；无 Job/Worker/终态路径 |
| `tests/test_aiqe_regression_api.py`（365 行，14 例） | **真实 HTTP**（`TestClient` + 依赖覆盖） | 40 位 SHA、部署证明、fingerprint 幂等、范围冻结/排除原因、终态同步与对比快照、取消、权限、404、跨项目 source Run | **部分合格**：是 G4 中唯一从正式 API 进入的文件；但 **0 次**引用 `ExecutionJob`（`:156-191` 只断言 Run=QUEUED 与节点 key）；`_complete_run`（`:223-249`）手工改 Run/Node/Assertion 终态，完全绕过 Worker；源 Run 只有 1 个无依赖节点（`:78-106`），无法验证 DAG 复制 |
| `tests/test_aiqe_defect_regression.py`（81 行，7 例） | 直调 `defect_service.create_regression`（旧服务，非 AIQE regression_service） | 旧回归表字段、短 SHA 拒绝、compare_runs | **不合格（对本 Issue）**：与本 Issue 的 `regression_service`/Job 链路无关 |

**结论（V16-006 测试）**：规格 4 条验收（E1–E6 终端结果、Regression 可查 Job 并消费到终态、同幂等键同 Run、Outbox relay 崩溃恢复）**0 条**被覆盖；triage 测试反而把违规状态写成断言。

## 4. V16-007 详审：冻结并完整复制 DAG Snapshot

### 4.1 关键证据

1. **无不可变快照实体。** `git grep -n "WorkflowSnapshot\|SnapshotCloner\|snapshot_cloner"` 全仓 0 命中；`alembic/versions` 最新到 `20261125_merge_aud_v15_pr595`，无 snapshot 相关迁移。Run 侧只有 `workflow_checksum`（`models/run.py:58`）+ 内联 `workflow_snapshot_json`（`:59`）。
2. **克隆丢弃 DAG（实测）。** 基线 `login(depends_on=[]) → verify(depends_on=["login"])` + `edges[{from:login,to:verify,condition:success}]`；克隆后节点 `depends_on` 全为空、`edges=[]`：
   - triage：`triage_service.py:255-267`（`"depends_on": []` 在 `:262`，`"edges": []` 在 `:266`）；
   - regression：`regression_service.py:214-226`（`:221` / `:225`）；
   - 实测克隆节点 `[('login','PENDING'), ('verify','PENDING')]`，无任何依赖（附录 B·A/B）。
3. **克隆丢弃断言与执行语义（实测）。** 克隆 node dict 只有 `key/driver/input/depends_on`（同上）；`NodeRun.assertions_json` 实测 `[]`（附录 B·A），`outputs/output_schema/type/capability/resource_keys/platform/retry_policy` 一律丢失。这意味着即便以后补上 Job，克隆出的业务节点也没有 Oracle（V16-009 的输入被掏空）。
4. **克隆 Run 无快照/checksum。** `TestRun` 两个字段均未赋值（`triage_service.py:231-245`、`regression_service.py:344-372`），实测 `workflow_checksum=''`、`workflow_snapshot_json={}`。下游 `quality_gate_service.py:177-189` 用 `run.workflow_checksum` 汇总 `contract_checksum`，空串导致质量门禁无法绑定快照。
5. **无 clone diff（节点级）。** 回归只记录 case 级 excluded（`regression_service.py:166-179,330`），triage 的 `snapshot_diff` 只比较 Run 的不可变字段与 env snapshot（`triage_service.py:160-173`），都不含节点级排除原因；克隆后所有节点恒无依赖，正是规格步骤 6 禁止的“静默变成无依赖”。
6. **无 schema 版本迁移器。** `schema_version` 仅存在于 `WorkflowDefinition`（`models/workflow.py:38`）与 graph 字典，Run/快照无版本字段；`workflow_validator.py:109-110` 只校验非空；不存在“不支持版本 → BLOCKED”。
7. **克隆路径不校验图。** `validate_workflow()`（`workflow_validator.py:92-247`，含环路/缺依赖/边端点/未知变量引用）只在 `launch_run` 调用；triage/regression 直接 `dag_scheduler.create_node_runs()`（`dag_scheduler.py:112-134`），无校验。
8. **“运行中禁止改 graph”只保护源定义。** `workflow_service.update_graph` 对 approved 定义抛错（`workflow_service.py:69-81`），但 Run 的内联 JSON 列没有不可变约束，任何代码/SQL 都能改。

### 4.2 V16-007 gaps

- **G4-007-01（P0）** 无 `WorkflowSnapshot` 模型/表/迁移（0 命中）。
- **G4-007-02（P0）** 克隆硬编码空 DAG：`triage_service.py:262,266`、`regression_service.py:221,225`（实测）。
- **G4-007-03（P0）** 克隆丢弃 assertions/outputs/type/capability/resource_keys（实测 `assertions_json=[]`）。
- **G4-007-04（P1）** 无 `SnapshotCloner`，两处手写复制（`triage_service.py:249-268`、`regression_service.py:207-227`），违反步骤 3。
- **G4-007-05（P1）** 克隆 Run 无 `workflow_checksum`/`workflow_snapshot_json`（实测 `''`/`{}`），快照哈希不可得。
- **G4-007-06（P1）** 无节点级 clone diff 与排除原因：`regression_service.py:166-179`（只有 case 级）。
- **G4-007-07（P1）** 无快照 schema 版本与 migrator，无“旧版本 BLOCKED”：`models/workflow.py:38`、`workflow_validator.py:109-110`。
- **G4-007-08（P2）** 运行中 graph 不可变仅靠约定；`models/run.py:59` 为可写 JSON。
- **G4-007-09（P2）** 克隆路径不复用 `validate_workflow`：`dag_scheduler.py:112-134`。
- **G4-007-10（P1）** 验收测试缺失：无 8 节点/分支/并行/汇合/动态输出 clone 测试；现有基线图无 edges（`test_aiqe_triage_experiments.py:27-34`）、回归源 Run 仅 1 节点（`test_aiqe_regression_api.py:78-106`）。

### 4.3 V16-007 已存在测试及入口质量

- 无任何 `WorkflowSnapshot`/`SnapshotCloner`/clone-diff 测试（全仓 0 命中）。
- 与克隆相关的两条用例见 §3.3 的 triage/regression 表：都用“无边图/单节点图”，因此**结构上不可能**发现 `edges=[]`、`depends_on=[]`、断言丢失；断言只到“节点 key 集合”与 `status == "QUEUED"`。
- `tests/test_aiqe_dag_scheduler.py:17-33` 的 `diamond()` 确实有 4 节点 + 4 边，但**没有任何用例把它用于克隆**（只用 `schedule/complete_node`），是可直接复用的现成 fixture。

## 5. 交叉发现

### 5.1 文档声明与实测冲突（规格 §0.2.8 明确禁止以文档声明作证据）

| 文档 | 声明 | 实测 |
|---|---|---|
| `docs/aiqe/baseline.md:899` | “FIX-006 Run Launch / 对账 ✅ 已实现” | 对账 CLI 成功路径 TypeError（G4-005-11）；Reconciler 漏 QUEUED/Job-success/证据校验（G4-005-04/05/06） |
| `docs/aiqe/aud-remediation-v15-final-report.md:35,63` | “fencing token、生命周期事件、Reconciler、租约过期回收”已交付 | fencing 未接入任一正式写路径（G4-005-01）；7 个规格事件名 0 命中（G4-005-07） |
| `docs/aiqe/triage_service.py:6-8`（模块 docstring） | “通过**统一 Run 创建路径**生成真实 TestRun” | 该路径不调用 `launch_run`、不建 Job（G4-006-02） |
| `run_launch.py:6`（模块 docstring） | “一个 NodeRun 最多一个 ExecutionJob（DB 唯一约束…）” | 无该唯一约束（G4-005-03） |
| `docs/aiqe/ops.md:67-71` | 对账 CLI“必须定时”执行 | CLI 崩溃；`deploy/` 无 cron/compose 配置 |

### 5.2 状态机与规格命名不一致，且无差异说明/ADR

规格 V16-005 定义了 Run/NodeRun/Job 三套状态名；实现是 v1.4 的 `DRAFT/VALIDATING/QUEUED/RUNNING/…+outcome`、`pending/running/success/failed/canceled/expired`、`PENDING/READY/…/CANCELED`。规格第 11 行要求“与当前源码不一致之处，先提交差异说明和 ADR”；仓库 `docs/adr/` 未见对应 ADR，`docs/aiqe/v1.6/` 也无差异说明。**这是评审可直接质询的合规缺口**（不是代码 bug，但会让 V16-005 无法被判 VERIFIED）。

### 5.3 与本组其它 Issue 的边界（避免重复计账）

- `launch_experiment`/`create_experiment_api` 无项目作用域校验（`api/v1/aiqe_triage.py:45-66,69-83`；`triage_service.py:176-219,272-299`）→ 归 **V16-011（租户边界）**，本报告只作交叉标注。
- 克隆后无断言 / Reconciler 无断言证据即 PASS → 归 **V16-009（Assertion 与 PASS 语义）**；本报告只说明 V16-005/007 造成的输入缺失。
- “QUEUED 即 PASS / 回归通道无 Job” 与 **G8（V16-017 E2E）** 的发现一致，证据可互相引用。
- 外部 Runner 上报缺少 attempt/token 的契约属于 V16-005；如果 V16-001 之后 `node_executor.execute_node` 需要 `policy_context`，也不会改变本报告的租约结论。

### 5.4 可观测性/运维面

- 无 `JOB_CLAIMED`/`FENCING_REJECTED` 事件 → 生产上“谁在何时认领、迟到结果被拒”不可审计。
- `ReconcileReport` 的计数字段（`nodes_closed/jobs_failed/runs_completed`）在部分分支不递增（如 `job.success` 无分支；`expired` 分支同时 `nodes_closed += 1` 与 `jobs_failed += 1`，语义混用），即使 CLI 修好也会给出误导性统计。
- 事件 outbox 无人消费 → SSE 之外没有任何“事件驱动”的下游（回归终态同步必须靠 API 懒加载，见 `regression_service.py:477-495`）。

## 6. 可复核命令

以下命令均在仓库根目录执行（`F:\CamelTv-worktrees\DeepSeek_Harness-aiqe-v1-6`）。

```powershell
# 0. 基线
git rev-parse HEAD            # 期望 86a44b2cbb7c9c44d3ef6af1e324d1f42c3eae6f
git status --porcelain        # 审计时刻：18 项 M + docs/aiqe/v1.6/ 等未跟踪（V16-001 在途）

# 1. V16-005：fencing/租约校验是否接入正式写路径
git grep -n "assert_writable\|assert_current\|bump_fencing_token\|StaleLeaseError" -- test-platform-v2/backend/app
#   期望：只有 lease.py 自身、job_consumer.py(claim/complete_from_report)、dag_scheduler.complete_node
git grep -n "complete_from_report(" -- test-platform-v2/backend/app
#   期望：api/v1/execution_jobs.py:205 一处，且无 fencing_token 参数
git grep -n "fencing_token\s*=" -- test-platform-v2/backend/app/aiqe/services
#   期望：仅 lease.py / resource_lock.py；StepAttempt 永不赋值

# 2. V16-005：Job 幂等唯一键
git grep -n "execution_kind" -- test-platform-v2/backend
#   期望：0 命中
python -c "print(open('test-platform-v2/backend/app/models/execution_job.py').read().count('run_id'))"
#   期望：0（execution_jobs 无 run_id/node_run_id/attempt_no 列）

# 3. V16-005：Reconciler 覆盖面
git grep -n "TestRun.status == \"RUNNING\"\|job.status == \"pending\"\|job.status in {\"failed\", \"canceled\"}" -- test-platform-v2/backend/app/aiqe/services/reconciler.py
#   期望：153 / 263 / 197；无 job.status == "success" 分支、无 QUEUED 扫描

# 4. V16-005：规格审计事件名
git grep -n -E "JOB_CLAIMED|LEASE_RENEWED|LEASE_EXPIRED|FENCING_REJECTED|JOB_RETRIED|NODE_FINALIZED|RUN_FINALIZED" -- test-platform-v2/backend
#   期望：0 命中

# 5. V16-006：Outbox relay 是否有消费者
git grep -n "consume_terminal_events\|dispatch_outbox" -- test-platform-v2/backend
#   期望：只有定义处与 tests；无 worker/CLI/lifespan 调用

# 6. V16-006：契约字段
git grep -n "workflow_snapshot_id\|execution_kind\|LaunchResult" -- test-platform-v2/backend/app
#   期望：0 命中

# 7. V16-006/007：克隆丢边
git grep -n -A2 "\"depends_on\": \[\]" -- test-platform-v2/backend/app/aiqe/services/triage_service.py test-platform-v2/backend/app/aiqe/services/regression_service.py
#   期望：triage_service.py:262、regression_service.py:221

# 8. V16-007：不可变快照实体
git grep -n -E "WorkflowSnapshot|SnapshotCloner|snapshot_cloner" -- .
#   期望：0 命中

# 9. 对账 CLI 崩溃（只读语义验证，不连库）
python -c "from dataclasses import dataclass
@dataclass
class R:
    a: int = 1
    def __getitem__(self, k): return self.a
    def get(self, k, d=None): return self.a
print({'ok': True, **R()})"
#   期望：TypeError 'R' object is not a mapping —— 对应 scripts/qa/aiqe_reconcile.py:32

# 10. 现有测试（审计时刻 83 passed；全绿不代表满足规格）
cd test-platform-v2/backend
python -m pytest -q tests/test_aiqe_aud006_state_recovery.py tests/test_aiqe_reconciler.py `
  tests/test_aiqe_executor_consumer.py tests/test_aiqe_run_launch.py `
  tests/test_aiqe_triage_experiments.py tests/test_aiqe_regression_api.py tests/test_aiqe_dag_scheduler.py
#   审计时刻结果：83 passed, 7 warnings in 7.04s

# 11. 实测脚本（仓库外；内存 SQLite；见附录 B）
$env:PYTHONPATH="."
python C:\Users\26029\AppData\Local\Temp\g4_verify.py
python C:\Users\26029\AppData\Local\Temp\g4_verify2.py
python C:\Users\26029\AppData\Local\Temp\g4_verify3.py
```

## 7. 最小整改建议（按 Issue；只给文件/函数与必须新增的负向测试，不含补丁代码）

### 7.1 V16-005

1. `app/aiqe/services/dag_scheduler.py:complete_node()`：把 `fencing_token` 改为**必填**（或新增内部 `_finalize_node_with_fence()`），进入前执行 `lease.assert_current(..., job_expires_at=job.lease_expires_at)`；终态节点拒绝任何回写（`row.status in NODE_TERMINAL` → 抛 `TerminalNodeImmutable`），重跑必须新建 Attempt。
2. `app/aiqe/services/execution_service.py:finalize_node()` / `execute_inprocess_job()`：从 `ExecutionJob.attempt` 取 token 并透传；执行结束时用**条件 UPDATE**（`WHERE id=? AND node_id=? AND attempt=? AND status IN ('running')`）写 Job，rowcount=0 → 丢弃结果并记 `FENCING_REJECTED` 事件。
3. `app/api/v1/execution_jobs.py:report`：`ReportRequest` 增加 `attempt`/`fencing_token`（必填），透传给 `complete_from_report`；缺失 → 409，不进入收口。
4. `app/models/execution_job.py` + 新 alembic 迁移：新增 `run_id/node_run_id/attempt_no/execution_kind` 列与 `UNIQUE(run_id,node_run_id,attempt_no,execution_kind)`；`execution_dispatcher.enqueue_node_run()` 写入这 4 列并捕获 IntegrityError 返回既有 Job；删除 `run_launch.py:6` 的错误声明。
5. `app/aiqe/services/reconciler.py`：新增 (a) `TestRun.status == "QUEUED"` 且无 pending Job 超过 SLA → `ERROR/BLOCKED` + 原因事件；(b) `job.status in {"success","succeeded"}` 且 node 未终态 → 依据 Attempt/Assertion/Artifact 重建或 `ERROR`；(c) `_finalize_run()` 复用 `artifact_service.incompleteness_reasons()` 与 required assertion 校验，不足 → `INCOMPLETE/UNKNOWN`；(d) 去掉 `except (…): pass`，失败写 `LEASE_RENEWED/FENCING_REJECTED` 类事件。
6. `app/aiqe/services/reconciler.py` + `job_consumer.py`：按规格补齐 7 个事件名（可在 payload 中保留旧名做兼容映射），特别是 `JOB_CLAIMED`（claim 处）、`LEASE_RENEWED`（heartbeat 处）、`FENCING_REJECTED`（两处拒绝分支）、`NODE_FINALIZED`/`RUN_FINALIZED`（收口处）。
7. `scripts/qa/aiqe_reconcile.py:32`：改为 `stats.payload()`；新增 CLI 冒烟测试（subprocess，断言退出码 0 与 JSON 可解析）。
8. 必须新增的负向测试（全部从 Worker/API/CLI 正式入口进入）：
   - `execute_inprocess_job` 在租约过期/节点被 requeue 后执行 → 结果被丢弃、Job/Node 状态不变、写 `FENCING_REJECTED`；
   - `POST /execution-jobs/{id}/report` 不传 `fencing_token` → 409；旧 token → 409 且 Node 仍 RUNNING；
   - 同一 Job 重复投递 2/10/100 次（`consume_once` + 手工重复 claim）→ 只有 1 个终态 Attempt、外部副作用计数 1；
   - 终态节点收到迟到结果 → `TerminalNodeImmutable`，状态不变；
   - Reconciler 连跑 10 次 → 事件数/状态不变（幂等）；
   - QUEUED 无 Job（用 triage/regression 真实产出）→ SLA 内转 `BLOCKED/ERROR` 且事件含原因；
   - job=success + node=RUNNING + `PENDING_UPLOAD` artifact → 不得 `PASS`（`INCOMPLETE/UNKNOWN`）。

### 7.2 V16-006

1. `app/aiqe/services/run_launch.py:launch_run()`：按规格重塑签名（`workflow_snapshot_id`、`execution_kind`、`idempotency_key`、requested_by…），返回 `LaunchResult` 数据类（`run_id/run_status/job_ids/node_run_ids/snapshot_hash/dispatch_status/blocked_reason`）。
2. `app/aiqe/services/triage_service.py:default_run_launcher()` / `launch_experiment()`：删除自建 `TestRun`，改为 `launch_run(..., execution_kind="NOISE_EXPERIMENT", source_run_id=baseline.id, experiment_id=row.id)`；保留单变量快照校验。
3. `app/aiqe/services/regression_service.py:create_regression_request()` / `_replicate_nodes()`：删除自建 `TestRun` 与手写复制，改为 `launch_run(..., execution_kind="DEFECT_REGRESSION", source_run_id=..., defect_id=..., requested_scope=mandatory)`；`blockers_json` 非空时返回 `LaunchResult(blocked_reason=...)`。
4. `app/aiqe/services/run_launch.py`：把 `dag_scheduler.schedule()` 后再置 RUNNING 的逻辑改为“派发即返回 QUEUED”；把 `QUEUED→RUNNING` 迁移移到 Worker claim 成功后（`job_consumer.claim_aiqe_jobs` / `execution_job_service.claim_job`）。
5. Outbox：新增 job 派发表（或复用 `event_outbox` + 类型区分）与 relay 循环（lifespan/独立 worker + CLI），relay 幂等（`SELECT … FOR UPDATE SKIP LOCKED` / 条件 UPDATE），失败重试上限后 `DEAD`；补 `dispatch_outbox` 的真实发布实现与调用方。
6. `app/aiqe/services/preflight.py`：补 TargetPolicy 解析、Query Registry 解析、mandatory scope 非空校验；不通过即 `BLOCKED`（不得进入 QUEUED）。
7. 必须新增的负向/正向测试（从 REST API 进入）：
   - `POST /api/v1/aiqe/experiments/{id}/launch` → 断言 `LaunchResult.job_ids` 非空、DB 中存在 pending Job、Run 为 QUEUED/ACCEPTED 而非 RUNNING；
   - `POST /api/v1/aiqe/defects/{id}/regressions` → 同上；随后由真实 `job_consumer` 消费到终态，断言 Run `COMPLETED` 且 compare 可用；
   - 同 `idempotency_key` 并发/重复请求 2/10 次 → 1 个 Run、1 个 Job；
   - relay 崩溃（进程内模拟异常）→ 重启后 Job 仍被消费且只消费一次；队列不可用 → Job 不丢；
   - mandatory scope 为空/Driver 缺失 → launch 返回 `blocked_reason` 且无 Job（与 V16-008 联测）。

### 7.3 V16-007

1. 新增 `app/aiqe/models/snapshot.py` + alembic 迁移：`workflow_snapshots(id, project_id, source_workflow_id, source_revision, schema_version, canonical_json, sha256, created_at, created_by)`，只追加不改写；`node_specs` 可存 JSON（或独立表），并加 `UNIQUE(project_id, sha256)`。
2. 新增 `app/aiqe/services/snapshot_service.py`：`freeze_snapshot(db, workflow)`（canonical json.dumps(sort_keys,separators) + sha256 + schema_version + source revision）与 `SnapshotCloner.clone(db, snapshot, *, scope, excluded_reasons)`：
   - 复制 `depends_on/edges/condition/type/assertions/outputs/output_schema/capability/resource_keys/secret_keys/retry_policy/timeout`；
   - 节点新 ID 后**重写 edge endpoints**（或保留 key 但显式记录映射）；
   - 排除节点必须写 `excluded_reasons`，且**禁止**让被排除节点成为其它节点的唯一父节点（发现即抛 `CLONE_DEPENDENCY_BROKEN`）；
   - 返回 `clone_diff`（added/removed/retyped/edges_changed）。
3. `triage_service.default_run_launcher()` / `regression_service._replicate_nodes()`：改为调用 `SnapshotCloner`，并把 `snapshot.sha256` 写入 `LaunchResult.snapshot_hash` / `TestRun.workflow_checksum`、把 `snapshot.canonical_json` 写入 `TestRun.workflow_snapshot_json`（或直接存 `workflow_snapshot_id`）。
4. `workflow_validator.py`：新增 `SNAPSHOT_SCHEMA_VERSION` 与 `migrate_snapshot(v)`；未知版本 → `BLOCKED/SNAPSHOT_SCHEMA_UNSUPPORTED`，并在 `SnapshotCloner` 入口调用 `validate_workflow`。
5. 必须新增的测试：
   - 8 节点 DAG（分支 + 并行 + 汇合 + 条件边 + 动态输出）clone：断言拓扑序、节点数、边数、入度/出度、条件边与源快照一致；canonical hash 除允许字段外一致；
   - 克隆后断言 `assertions_json`/`outputs_spec_json`/`capability`/`resource_keys` 与源一致；
   - 缺失父节点 / 循环 / 未知节点引用 → clone 抛错（不得静默）；
   - 排除父节点但保留子节点 → 拒绝（`CLONE_DEPENDENCY_BROKEN`）；
   - 旧 schema 版本快照 → `BLOCKED`；
   - `excluded_reasons` 与 clone_diff 落库可查。

## 8. 结论与建议的 Issue 状态

| Issue | 审计状态 | 允许关闭的前置条件 |
|---|---|---|
| V16-005 | **PARTIAL** | 完成 §7.1 的 1–3（token 强制 + 条件更新）、5（Reconciler 三类缺口 + 证据校验）、6（事件）、7（CLI），并补 §7.1.8 的 7 条负向测试；否则不得进入 `VERIFIED` |
| V16-006 | **MISSING** | 完成 §7.2 的 1–4（契约 + triage/regression 改造 + RUNNING 时点）、5（outbox relay）、6（preflight），并补 5 条 API 级测试 |
| V16-007 | **MISSING** | 完成 §7.3 的 1–4（不可变快照 + SnapshotCloner + 版本迁移 + 接入两处），并补 6 条 clone 测试 |

> 规格第 199 行的阶段出口条件明确：“V16-005～009 完成后，才允许回归和 Noise 自动化”。当前 V16-005/006/007 均未达出口条件，因此 **Noise E1–E6 与 Defect Regression 的自动化验收不得开始**，即使它们的 API/表结构已存在。

## 附录 A：审计时刻文件快照（SHA256，用于行号对齐）

| 文件 | 字节 | SHA256 |
|---|---|---|
| `test-platform-v2/backend/app/aiqe/services/lease.py` | 3639 | `70C7432195DD1034DB681FC85356C1F186F63C56E469CFA4AE3F3F4E3C4046DD` |
| `test-platform-v2/backend/app/aiqe/services/job_consumer.py` | 6684 | `D8272DE9F1C43BB351B4BADA3E9034AC195E509B8F4FF665656611A078476A1C` |
| `test-platform-v2/backend/app/aiqe/services/reconciler.py` | 13556 | `64DBE887890D38873D14AFA524815930FF60080FB1433A1A39729B8D7CF37E64` |
| `test-platform-v2/backend/app/aiqe/services/run_launch.py` | 11671 | `C5ABD7A22C2D32EEFC02AACA70E720F838CD4EDA0DB420BBBF49C4F7934F1EE6` |
| `test-platform-v2/backend/app/aiqe/services/triage_service.py` | 14001 | `DAE3248B8EC06AEA6C7400156BBB995105BDC0FD0DEF25D468154C4654D7199F` |
| `test-platform-v2/backend/app/aiqe/services/regression_service.py` | 17299 | `108F9CCB6FAF8C4D5C862258A01CD0412EBC2E48CF18414F9DD0E1D79C34A833` |
| `test-platform-v2/backend/app/aiqe/services/dag_scheduler.py` | 18864 | `2055DE549C5B6B57B390E5BD56972669EDAB535CCC59F2E4DCC800A56DEE7C06` |
| `test-platform-v2/backend/app/aiqe/services/execution_service.py` | 33534 | `C72A74C86717351969C0BE3319ED4A7AB201F0E6471623C7532460CABC689640` |
| `test-platform-v2/backend/app/aiqe/services/execution_dispatcher.py` | 3295 | `AD1099BEB33F106DBBA16C165064D81DA2EA937D6CBCDE9578AF736EBEEB5406` |
| `test-platform-v2/backend/app/aiqe/services/regression_terminal.py` | 11633 | `F39861AE8FBD06665F19D830413C769BE104C8FD63DC62773AC2ABE52D185CDB` |
| `test-platform-v2/backend/app/aiqe/services/event_service.py` | 4852 | `EC27599A442B94868C14549756BD0E21F577D5D0684F2DF60E20481BF35F5564` |
| `test-platform-v2/backend/app/aiqe/models/run.py` | 12007 | `BAECEFEB7CABDD4CEF610C00F6FB81949AD43C4894B1BD00CF65269A0B18D3B8` |
| `test-platform-v2/backend/app/models/execution_job.py` | 2412 | `76D19CD9FF4D460F96199AF76021EE30F5800253C4E8DEDC8E828173F4CCBF3A` |
| `test-platform-v2/backend/app/api/v1/execution_jobs.py` | 12530 | `09C74A6A0A7CB1510F7F3618D9A3B5EC6E1C5E2F7DD2F78EAC5035D9700AD4A8` |
| `test-platform-v2/backend/app/api/v1/aiqe_runs.py` | 15530 | `B4A20534DBB136790F3BF40F9AF8F48236A268B12E919D8DE5FD0BB49EDC8AA0` |
| `test-platform-v2/backend/app/api/v1/aiqe_triage.py` | 7070 | `0A1A9D711F16D86EF275B45F2150AC30E6F1C9A336FDFAE7E46EDC594B1A48C0` |
| `test-platform-v2/backend/app/api/v1/aiqe_regressions.py` | 9381 | `8EE41E5C7F2494692CFFBB92EE044AB8E55575D53BA6B485C1835682928C79F3` |
| `scripts/qa/aiqe_reconcile.py` | 1425 | `3958DE88542A368D147778F6FB848511B5439A7E6A4398C44642D98B9C3E34BF` |

测试文件（只用于入口质量判定，行号同上）：`test_aiqe_aud006_state_recovery.py`(337)、`test_aiqe_reconciler.py`(118)、`test_aiqe_executor_consumer.py`(152)、`test_aiqe_run_launch.py`(402)、`test_aiqe_triage_experiments.py`(331)、`test_aiqe_regression_api.py`(365)、`test_aiqe_dag_scheduler.py`(143)。

## 附录 B：实测脚本与输出（仓库外临时脚本，内存 SQLite）

脚本位于 `%TEMP%\g4_verify.py`、`%TEMP%\g4_verify2.py`、`%TEMP%\g4_verify3.py`；运行方式 `cd test-platform-v2/backend; $env:PYTHONPATH="."; python <script>`。它们只创建内存库、调用现有 service/API 层，不写仓库、不连真实数据库。

### B·A/B/C/D（g4_verify.py）

```
== A. triage clone ==
verification_run.status = QUEUED
verification_run.workflow_checksum = ''
verification_run.workflow_snapshot_json = {}
ExecutionJob count = 0
cloned nodes (key,status) = [('login', 'PENDING'), ('verify', 'PENDING')]
cloned assertions_json = [('login', []), ('verify', [])]
== C. reconciler on QUEUED run w/o job ==
run.status after reconcile = QUEUED
reconciler runs_scanned = 0 nodes_closed = 0
experiment status = QUEUED
== B. regression ==
regression.status = QUEUED created = True
regression_run.status = QUEUED
regression_run.workflow_checksum = ''
regression_run.workflow_snapshot_json = {}
ExecutionJob count (after regression) = 0
cloned regression nodes (key,status) = [('login', 'PENDING'), ('verify', 'PENDING')]
== D. aiqe_reconcile CLI payload ==
CLI success-path failure: TypeError 'ReconcileReport' object is not a mapping
```

### B·E/F（g4_verify2.py）

```
== E. fencing_token omitted on the formal report path ==
with fencing_token=2 -> {'job_id': 1, 'skipped': True, 'reason': 'STALE_LEASE', 'node_status': 'RUNNING'}
with fencing_token=None -> {'status': 'PASSED', 'node_status': 'PASSED', 'skipped': False, 'node': None, 'error_class': ''}
execution_service call count with token=None = 1
== F. terminal node overwrite ==
node status after PASSED = PASSED
node status after late FAILED (no fencing token) = FAILED
```

（E 中的 `execution_service.complete_from_external_report` 被替换为记录调用的桩函数，只为证明“控制流确实前进了”；token 缺失即放行的**代码条件**在 `job_consumer.py:114`，不依赖该桩。）

### B·H/I（g4_verify3.py）

```
== H. job success but node RUNNING ==
node.status after reconcile = RUNNING
run.status after reconcile = RUNNING
stats.nodes_closed = 0 finalized_runs = []
== I. all nodes PASSED but artifact PENDING_UPLOAD ==
run2.status/outcome from reconciler = COMPLETED PASS
== I2. same facts through dag_scheduler.finalize_run (execution path) ==
run3.status/outcome from dag_scheduler = COMPLETED INCOMPLETE
```
