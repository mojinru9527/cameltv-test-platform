# DEV-batch-162-c161-conditions 看板

> 批次: batch-162-c161-conditions | Executor: codex | 状态: ✅ 已关闭（PR #227/#228/#229）

## Slice
| # | Slice | 状态 |
|---|-------|------|
| S0 | worktree + PRD/PM/Design | ✅ |
| S1 | C161-1: DATA_DIR 持久卷 + 文档 | ✅ |
| S2 | C161-2: 调度 environment_id（模型/迁移/服务/调度器/前端） | ✅ |
| S3 | C161-3: surface 规则扩展（派生值，无回填） | ✅ |
| S4 | 硬门禁（ruff ✅ pytest 1387 ✅ alembic ✅ tsc/build/vitest 460 ✅） | ✅ |
| S5 | 生产复验：调度绑定 env3 触发成功（run#9）、surface 其他=0、Cookie 持久化待用户凭据 | ✅ |
| S6 | 收尾：Dockerfile chown 热修、回填脚本移除、C162-1/2 登记 | ✅ |

## 批次记录
| 项 | 值 |
|----|----|
| PR | #227（功能）+ #228（Dockerfile 热修）+ #229（清理脚本）全部合入 |
| C 条件 | C161-1/2/3 关闭；新增 C162-1/2（复验遗留） |
