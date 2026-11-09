# Batch 279（M1 / TA-005）— Design

> **部门**：🟪 Design · **日期**：2026-11-10

## 1. 数据模型

| 表 | 主键 | 关键约束 | 关系 |
|----|------|----------|------|
| `test_runs` | UUID string(36) | `uq(project_id, run_key)`；索引 `(project_id, created_at)`、`(scenario_id, created_at)`、`commit_sha`、`retest_of`、`status` | 1:N node_runs；自引用 retest_of |
| `node_runs` | UUID | `uq(run_id, node_key)`；`execution_job_id` 1:1 旧派发 | N:1 test_runs；1:N step_attempts |
| `step_attempts` | UUID | `uq(node_run_id, step_key, attempt_no)`（Attempt 永久保留） | N:1 node_runs；1:N assertion |
| `run_assertion_results` | UUID | `uq(step_attempt_id, assertion_key)` | N:1 step_attempts |

外键：
- `test_runs.project_id → sys_project.id`（CASCADE）
- `test_runs.scenario_id → test_scenarios.id`（SET NULL，**BIGINT**，D-279-2）
- `test_runs.environment_id → environment.id`（SET NULL）
- `test_runs.retest_of → test_runs.id`（SET NULL）
- `test_runs.trigger_user_id → sys_user.id`（SET NULL）
- `node_runs.execution_job_id → execution_jobs.id`（SET NULL）
- 子表全部 CASCADE 到 Run。

## 2. 状态机（唯一入口 `run_state.transition()`）

```text
DRAFT → VALIDATING → QUEUED → RUNNING
RUNNING → WAITING_HUMAN / TRIAGING / COMPLETED
WAITING_HUMAN → RUNNING
TRIAGING → RUNNING / COMPLETED
任意非终态 → BLOCKED / CANCELED / ERROR
```

不变量：
1. `COMPLETED` 必须 `outcome ∈ {PASS, FAIL, INCOMPLETE, UNKNOWN}`；
2. `BLOCKED / CANCELED / ERROR` 必须 `outcome = NULL`；
3. 终态无出边；同状态迁移非法；
4. `apply_transition()` 只改内存，事务由调用方控制。

`can_transition()` 供 UI 预判，不抛异常；`transition()` 抛 `InvalidStateTransition`。

## 3. 迁移策略

`20261111_ta005_run_models`（down_revision `20261110_b277b_ui_run_exec_job`）：

1. 检查 `test_runs` 是否已存在；
2. 已存在且含 `run_key` → **直接返回**（初始迁移 `Base.metadata.create_all` 已在
   SQLite/新库提前建全量表，D-279-3）；
3. 已存在但无 `run_key`（旧 AITDE 遗留同名表）→ 按 PG `DROP ... CASCADE` / SQLite
   `drop_table` 清理后重建；
4. 不存在（生产路径）→ 正常 CREATE 四表 + 索引；
5. downgrade 逆序删四表。

## 4. 设计决策

| ID | 决策 | 理由 |
|----|------|------|
| D-279-1 | 新表命名 `run_assertion_results` | 既有 `assertion_results` 属 execution_runtime（7654 行、INT id、schema 不同），同名冲突且语义不同 |
| D-279-2 | `scenario_id` 用 BIGINT FK | `test_scenarios.id` 实为 INT；遵循“旧表外键 BIGINT”规则 |
| D-279-3 | 迁移检测已建表则跳过 | 初始迁移用 `Base.metadata.create_all`，新库会预建（含索引） |
| D-279-4 | 类名 `RunAssertionResult` | 与既有 `assertion_results` 模型解耦，避免导入歧义 |
| D-279-5 | `workflow_definition_id / execution_profile_id` 暂不建 FK | 对应表 M2 创建，避免悬空外键 |

## 5. 后续接口（batch-280/281 预留）

- Event 表 `run_events / event_outbox` 以 `run_id` 关联本批 `test_runs`；
- Artifact 表 `run_artifacts` 以 `run_id / node_run_id / step_attempt_id` 关联；
- Run API 读模型复用 `run_key + status + outcome` 三字段做列表。
