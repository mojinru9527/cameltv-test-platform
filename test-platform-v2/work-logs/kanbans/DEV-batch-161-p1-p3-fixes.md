# DEV-batch-161-p1-p3-fixes 看板

> 批次: batch-161-p1-p3-fixes | Executor: codex | 状态: 首轮 QA 通过，待总确认

## Slice
| # | Slice | 状态 |
|---|-------|------|
| S0 | worktree + 元数据 + PRD-lite | ✅ |
| S1 | G1: ai_tasks asyncio.run（cherry-pick 6988e3a）+ 回归测试 | ✅ |
| S2 | G2: 自动转缺陷链路补强（逐条容错 + batch-execute 触发 + 单测 3 个） | ✅ |
| S3 | G3: 蓝湖自动登录重试/持久化 Cookie/错误区分 + 单测 4 个 | ✅ |
| S4 | G4: execute-all 批量落库；删除/报告统计/任务详情透出复测（均正常，无需改码） | ✅ |
| S5 | G5: surface 推断 + Playground 错误内联 + 饼图格式 + 单测 6 个；新建用例表单复测计划 | ✅ |
| S6 | 硬门禁：ruff F821 ✅ / 后端全量 1376 ✅ / alembic 单头 ✅ / typecheck ✅ / build ✅ / vitest 460 ✅ | ✅ |
| S7 | 生产复验（合入+部署后，新模型重跑 G1/G2/G4/G5） | ⏳ |
| S8 | QA 报告 + Leader 判决 + 总确认 → PR/合入 | ⏳ |

## 批次记录
| 项 | 值 |
|----|----|
| 分支 | fix/p1-p3-fixes |
| 范围 | test-platform-v2/backend + frontend + work-logs + C-CONDITIONS.md |
| 档位 | light（修复档，PRD-lite + QA + Leader + 看板） |
| 首轮 QA | ruff ✅ pytest 1376 ✅ alembic 单头 ✅ tsc ✅ build ✅ vitest 460 ✅ |
| 生产复测 | DELETE /requirements/12 ✅ 报告统计 2/2 ✅ 任务详情错误透出 ✅ |
