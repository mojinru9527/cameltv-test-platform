# DEV-batch-161-p1-p3-fixes 看板

> 批次: batch-161-p1-p3-fixes | Executor: codex | 状态: 开发中

## Slice
| # | Slice | 状态 |
|---|-------|------|
| S0 | worktree + 元数据 + PRD-lite | ✅ |
| S1 | G1: ai_tasks asyncio.run（cherry-pick 6988e3a）+ 回归测试 | ✅ |
| S2 | G2: 自动转缺陷链路补强（逐条容错 + batch-execute 触发 + 单测） | ⏳ |
| S3 | G3: 蓝湖自动登录重试/持久化 Cookie/错误区分 | ⏳ |
| S4 | G4: execute-all 批量落库 + 接口任务失败原因透出 | ⏳ |
| S5 | G5: surface 推断/回填 + Playground 错误态 + 饼图格式 + 新建用例复测 | ⏳ |
| S6 | 硬门禁（ruff/pytest/typecheck/build/vitest）+ 生产复验（新模型） | ⏳ |
| S7 | QA 报告 + Leader 判决 + 总确认 → PR/合入 | ⏳ |

## 批次记录
| 项 | 值 |
|----|----|
| 分支 | fix/p1-p3-fixes |
| 范围 | test-platform-v2/backend + frontend + work-logs + C-CONDITIONS.md |
| 档位 | light（修复档，PRD-lite + QA + Leader + 看板） |
