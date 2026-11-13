# Batch 340（M9-1：attempt 持久化 + 重试策略 + attempt 查询 API）— PRD / Design / Dev

> mode: **full**（执行链路变更）· 分支：`feature/batch-340-attempts-retry` · 基线：`origin/main 7fb0af008`
> 排期来源：`work-logs/aiqe/M9-M10-plan-20261113.md` batch-340

## 1. 背景

TC-AIQE-003 要求"首次失败 + 重试成功不得掩盖失败"，但当前实现：

- `step_attempts` 表只有模型，**没有任何写入方**；
- `dag_scheduler.complete_node` 对 `FAILED` 直接按 fail_fast 阻断并收口 Run，**没有重试策略**；
- Run Console 只有 events/artifacts，没有 attempt 时间线可查询。

因此"重试"无法被证明，TC-003 只能 BLOCKED。

## 2. 目标

1. 节点每次进入 RUNNING 落一条 `step_attempts`（attempt_no 递增），失败 attempt **永久保留**；
2. `graph.retry.max_attempts`（1..5，默认 1）控制重试；失败且仍有额度 → 节点回 `PENDING`，Run 保持 `RUNNING`；
   fail_fast 时保持既有阻断语义；
3. 新增 `GET /api/v1/aiqe/runs/{run_id}/attempts`（`menu:aiqe_runs` 门禁），返回每节点完整 attempt 时间线；
4. 既有 DAG / Run API 行为不回归。

非目标：不做跨节点重试编排、不做 UI 展示（Console 展示列入 343/后续）、不改表结构。

## 3. 设计

| 点 | 实现 |
|----|------|
| attempt 写入 | `mark_running` 在 READY→RUNNING 时创建 `StepAttempt(status=RUNNING)`；`complete_node` 收口为终态 |
| 失败保留 | `_finalize_attempt` 不覆盖历史；重试追加 `attempt_no+1` |
| 重试 | `_retry_limit(graph)`；失败时 `attempt_count < limit` → 节点 `PENDING` 并提前返回（不 block 下游、不 finalize） |
| 查询 | `run_query_service.get_run_attempts` + 路由层序列化（路由禁 ORM 保持） |
| 权限 | 与 `/aiqe/runs/*` 一致：`menu:aiqe_runs` |

## 4. 验收

| # | 标准 | 证据 |
|---|------|------|
| A1 | 第一次 FAILED 保留，节点回 PENDING，Run 仍 RUNNING | `test_failed_attempt_kept_and_retry_runs` |
| A2 | 重试 PASSED 后 Run=PASS，attempts=[FAILED,PASSED] | 同上 |
| A3 | 无 retry 策略时保持原失败语义 | `test_no_retry_policy_keeps_failure` |
| A4 | API 返回 attempt 时间线与错误 | `test_attempts_api_returns_timeline` |
| A5 | 未知 Run 404；路由基线同步 | `test_attempts_api_404` + `test_route_inventory` |
| A6 | 既有 DAG/Run 测试全绿 | `test_aiqe_dag_scheduler.py` + `test_aiqe_run_api.py` |

## 5. 风险

| 风险 | 等级 | 处置 |
|------|:----:|------|
| 重试导致无限循环 | 低 | limit 上限 5；attempt_count 单调递增 |
| fail_fast 语义被重试绕过 | 低 | fail_fast 分支优先，保持原阻断 |
| 老 Run 无 StepAttempt | 低 | `_finalize_attempt` 缺失时按 attempt_count 补建 |
