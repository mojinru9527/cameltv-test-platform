# Batch 284（M2 / TA-010）— QA Report

> **部门**：🔍 QA · **日期**：2026-11-10

| # | 标准 | 结果 | 证据 |
|---|------|:----:|------|
| A1 | 串行→并行→汇聚 | ✅ | `test_serial_parallel_join_and_complete` |
| A2 | 并行上限 | ✅ | `test_parallel_limit_one` |
| A3 | fail_fast → Run BLOCKED（无 outcome） | ✅ | `test_fail_fast_blocks_run` |
| A4 | 资源锁互斥/释放后调度 | ✅ | `test_resource_lock_blocks_second_run` |
| A5 | Worker 重启恢复 | ✅ | `test_recover_resumes_running_node` |
| A6 | cleanup + Run PASS | ✅ | `test_cleanup_node_runs_after_terminal` |
| A7 | 锁 TTL/fencing/续租 | ✅ | `test_aiqe_resource_lock.py` 5 条 |
| A8 | Workflow 审批冻结 | ✅ | `test_aiqe_workflow_service.py` 4 条 |
| A9 | 全量 + ratchet | ✅ | 1429 passed / 43 skipped；PASS |

## 缺陷记录

| # | 现象 | 根因 | 修复 |
|---|------|------|------|
| 1 | SQLite naive/aware datetime 比较 TypeError | SQLite DateTime 不保留 tz | `_as_utc` 归一 + recover 侧同样处理 |
| 2 | ratchet：F841/RUF059/UP035 | 未用变量/导入位置 | 清理并改 `collections.abc.Callable` |
| 3 | ratchet：mypy Result.rowcount / Optional 比较 | 类型收窄 | 改 query.delete + 嵌套判空 |

## 风险

- 调度器未接 ExecutionJob（dispatch 回调），真实执行在 TA-012+；
- 条件边、规则 6 profile policy 未实现（见遗留登记）；
- 生产未部署本批（新增 2 表，窗口执行）。

## 判定

A1–A9 全绿，建议 Leader APPROVED。
