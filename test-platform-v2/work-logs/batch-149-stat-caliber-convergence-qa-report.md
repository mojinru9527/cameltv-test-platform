# Batch 149 — QA 报告（统计口径收敛 + 计划进度 0/0）

> **QA (🔍)** | Date: 2026-08-11 | Verdict: PASS

## 测试总览
| 条件数 | 通过 | 失败 | 阻塞 |
|--------|------|------|------|
| 2 (C147-3/C147-4) | 2 | 0 | 0 |

## 可执行门禁（命令、退出码、日志摘要）
| 门禁 | 命令 | 结果 |
|------|------|------|
| ruff F821 | `python -m ruff check app/ --select F821` | ✅ All checks passed |
| 受影响 pytest | `pytest tests/test_batch149_statistics.py tests/test_testplan.py tests/test_coverage_report.py tests/test_report_aggregator.py` | ✅ 39 passed |
| alembic heads | `python -m alembic heads` | ✅ 单头 20260811_batch148_exec_err |
| 前端 typecheck | `npm run typecheck` | ✅ |
| 前端 build | `npm run build` | ✅ |
| 前端 vitest | `npx vitest run` | ✅ 111 files / 450 tests |
| 本地冒烟 | Playwright（独立库） | 三端数字一致 + 进度 1/2 + 0 pageerror |

## 逐条件验证

### C147-3 统计口径收敛 5→1 + trace is_deleted + dashboard 执行计数
**变更文件**: backend/app/services/statistics_service.py（新增）、dashboard_service.py、trace_service.py

| 检查项 | 结果 | 说明 |
|--------|------|------|
| dashboard/trace 用例总数一致（is_deleted） | ✅ | 冒烟 3=3；单测 2=2（删除用例排除） |
| dashboard 执行计数 = test_execution | ✅ | 单测：删除用例的执行仍计数（2 条）；冒烟 manual exec=2 |
| trace 已执行/已通过口径 | ✅ | 冒烟 cases_executed=2 / cases_passed=1，与执行一致 |
| trace by_type/by_domain 补过滤 | ✅ | 单测 by_type 无 functional 残留 |
| 统一统计源 | ✅ | dashboard/trace 均调用 statistics_service |

### C147-4 计划列表进度 0/0
**变更文件**: backend/app/schemas/test_plan.py（PlanOut.stats）

| 检查项 | 结果 | 说明 |
|--------|------|------|
| GET /test-plans 返回 stats | ✅ | 单测 stats.total=2/pass_=1/pending=1 |
| UI 进度展示 | ✅ | 冒烟计划列表行显示「1/2」，截图 plan-list-progress.png |

## 缺陷列表
| # | 严重级 | 描述 | 证据 | 状态 |
|---|--------|------|------|------|
| 无 | - | - | - | - |

## 发布建议
状态: **READY**   必修复: 0   建议修复: 0

## 复盘卡
| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 计划 3h vs 实际 2.5h | 0/0/0/0 | 0 | - | 统计类改动先写口径表再编码 |

**技能使用**: cameltv-bug-guard（批量查询/防 N+1）；playwright-skill（冒烟证据）
