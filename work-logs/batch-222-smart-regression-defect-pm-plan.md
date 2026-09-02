# Batch 222 — PM Plan
> **PM (🟨)** | Date: 2026-09-05 | Executor: Codex | 完整批次

## 开发任务
### Task 1: recommend_regression_set + sync_defect_notification service
**描述**: 基于方案条目/模块/复用推荐回归集；缺陷同步写 NotificationLog。
**验收标准**: 推荐含模块回归 + 复用；sync 返回 synced。

### Task 2: API + route_inventory
**描述**: GET /regression-set、POST /defects/{id}/sync；route_inventory 631。

### Task 3: 前端推荐回归集 + 同步按钮
**描述**: src/api/versionTask.ts 增 getRegressionSet/syncDefect；[taskId].tsx 增推荐卡片 + 同步缺陷库按钮。
**验收标准**: typecheck/lint/build/vitest 绿。

### Task 4: 测试
**描述**: 后端 3 例；前端全量。
**验收标准**: 后端 18 通过；前端 608 通过。
