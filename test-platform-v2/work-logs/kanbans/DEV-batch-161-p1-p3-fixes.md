# DEV-batch-161-p1-p3-fixes 看板

> 批次: batch-161-p1-p3-fixes | Executor: codex | 状态: ✅ 已关闭

## Slice
| # | Slice | 状态 |
|---|-------|------|
| S0 | worktree + 元数据 + PRD-lite | ✅ |
| S1 | G1: ai_tasks asyncio.run + 回归 | ✅ |
| S2 | G2: 自动链路逐条容错 + batch-execute 触发 | ✅ |
| S3 | G3: 蓝湖自动登录重试/持久化/错误区分 | ✅ |
| S4 | G4: execute-all 批量落库；删除/统计/详情复测 | ✅ |
| S5 | G5: surface 推断 + Playground + 饼图 | ✅ |
| S6 | 硬门禁全绿 | ✅ |
| S7 | follow-up1/2/3（异步 project scope/持久化/链路 commit） | ✅ |
| S8 | 生产复验（新模型 deepseek-v4-flash）：G1✅ G2✅ G3部分✅ G4✅ G5✅ | ✅ |
| S9 | QA 报告 + Leader APPROVED + C 条件 + 关闭 | ✅ |

## 批次记录
| 项 | 值 |
|----|----|
| 分支 | fix/p1-p3-fixes + follow-up1/2/3（PR #221-#224，全部合入） |
| 档位 | light（修复档） |
| 门禁 | ruff ✅ pytest 1382 ✅ alembic 单头 ✅ tsc ✅ build ✅ vitest 460 ✅ |
| 生产复验 | 15.0.0 生成 338/导入 276；16.0.0 生成 405/导入 178；自动缺陷 4 + 自动报告 1；execute-all 405 条 3.4s；surface 其他 89→79 |
| C 条件 | C120-2 关闭；新增 C161-1/2/3 |
