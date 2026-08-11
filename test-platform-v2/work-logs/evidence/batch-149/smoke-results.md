# Batch 149 — 本地端到端冒烟证据（2026-08-11）

> 环境：worktree 独立 SQLite + 前端 5238 + 后端 8068。数据：3 有效用例（2 manual + 1 api）、计划 2 用例、执行 1 pass + 1 fail。

## 数字一致性（三端同口径）
| 来源 | 结果 |
|------|------|
| dashboard/stats | total_cases=3, api_cases=1, manual exec=2(pass1/fail1), pass_rate=50 |
| trace/coverage | total_cases=3, cases_in_plans=2, cases_executed=2, cases_passed=1, by_type={api:1,manual:2}, coverage=66.7%, execution=66.7%, pass_rate=50 |
| test-plans | stats={total:2, pass_:1, fail:1} |

- dashboard 执行计数不再为 0（修复前 manual exec=0）
- 追溯总数与工作台一致（is_deleted 过滤生效）
- 计划列表 UI 进度显示「1/2」（修复前恒 0/0），截图 `plan-list-progress.png`
- 页面 0 pageerror

## 硬门禁
| 门禁 | 结果 |
|------|------|
| ruff F821 | ✅ |
| 受影响 pytest（含新统计测试） | ✅ 39 passed |
| 前端 typecheck/build/vitest | ✅ 450 passed |
| alembic heads | ✅ 单头 |
