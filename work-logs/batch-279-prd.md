# Batch 279（M1 / TA-005）— Run 模型 + 状态机：PRD

> **部门**：🟦 Product · **日期**：2026-11-10 · **批次模式**：完整（新表/Schema/新行为）
> **分支**：feature/batch-279-m1-run-model · **基线**：origin/main `16ebdbfb7`
> **里程碑**：M1（Phase 1）第 1 批；M0 已于 2026-11-09 放行

---

## 1. 背景与问题

M0 清零后，平台已有执行派发（`execution_jobs`）与 UI 执行（`ui_test_run`），但缺少
**统一的执行事实源**：Run / 节点 / 步骤 / 断言四层没有模型，状态流转靠散落的字符串，
无法支撑后续 DAG、事件流、Artifact 与 Run Console。

TA-005 要落地 13 号 §4.7–§4.10 的四张表与 §5.1 状态机，作为 M1 其余任务的地基。

## 2. 目标

1. 建 `test_runs / node_runs / step_attempts / run_assertion_results` 四张表（Alembic）；
2. 实现 `run_state.transition()` 唯一入口，合法迁移单测全绿、非法迁移抛异常；
3. `node_runs.execution_job_id` 能关联既有 `execution_jobs`（旧派发单元）；
4. 不破坏现有 1332+ 后端测试与 alembic 单头。

## 3. 用户故事

- 作为 QA，我希望一次执行有稳定 `run_key`（`RUN-YYYYMMDD-NNNNN`）与状态/结论分离，
  以便区分“阻塞”和“通过”；
- 作为后端，我希望所有状态变更只经过一个函数，避免非法跳转写坏数据；
- 作为后续批次（M1-2/3/4），我需要 Run 作为 Event/Artifact/Console 的外键锚点。

## 4. 范围

### In scope
- 4 张新表 + 索引 + 唯一约束；
- TestRun 状态机（10 状态、终态、outcome 规则）；
- ORM 关系（Run→NodeRun→StepAttempt→Assertion）；
- 迁移 up/down 可重跑（SQLite 全链 + 生产 PG 路径）；
- 单测：状态机 + ORM 约束 + ExecutionJob 关联。

### Out of scope
- Run API / 事件流 / Artifact（batch-280/281）；
- Workflow/Scenario/ExecutionProfile 表（M2）；
- 旧 `version_task_run` 双写（M2 起）；
- 前端 Run Console（TA-008，M1 后段）。

## 5. 验收标准（可执行）

| # | 标准 | 证据 |
|---|------|------|
| A1 | 合法迁移全部通过（14 组） | `tests/test_aiqe_run_state.py` |
| A2 | 非法迁移抛 `InvalidStateTransition`（10 组 + 未知状态 + 同状态） | 同上 |
| A3 | COMPLETED 必须带 outcome；BLOCKED/CANCELED/ERROR 必须无 outcome | 同上 |
| A4 | 四表可建、唯一约束生效、级联删除生效 | `tests/test_aiqe_run_models.py` |
| A5 | `NodeRun.execution_job_id` 关联 `ExecutionJob` | 同上 |
| A6 | `alembic upgrade head → downgrade -1 → upgrade head` 通过 | QA 记录 |
| A7 | 全量后端回归无新增失败 | CI required |

## 6. 风险

| 风险 | 影响 | 缓解 |
|------|------|------|
| 旧 AITDE 同名表 `assertion_results`（7654 行） | 建表冲突 | 新表命名 `run_assertion_results`（D-279-1） |
| `test_scenarios.id` 实为 INT | UUID FK 失败 | 按 ID 规则用 BIGINT FK（D-279-2） |
| 初始迁移 `Base.metadata.create_all` | 新库提前建表导致重复 CREATE | 迁移检测已有 M1 schema 则跳过（D-279-3） |
| 生产 104 表 DROP 后 schema 漂移 | 迁移失败 | 生产先备份再升级（已完成） |
