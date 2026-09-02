# Batch 223 — PM Plan
> **PM (🟨)** | Date: 2026-09-05 | Executor: Codex | 完整批次

## 开发任务
### Task 1: 指标 + 对比 service
**描述**: get_operations_metrics（回归人天/周期/漏测/周活跃）；compare_versions（两版本覆盖/结论/缺陷）。
**验收标准**: 派生聚合正确；naive datetime 比较。

### Task 2: API + route_inventory
**描述**: GET /metrics/operations（metrics 路由）、GET /version-tasks/compare（在 /{task_id} 前）；route_inventory 633。

### Task 3: 前端 /metrics
**描述**: src/api/versionTask.ts 增 getOperationsMetrics/compareVersions；src/pages/metrics/index.tsx（4 卡片 + 对比）；路由 /metrics。

### Task 4: 测试
**描述**: 后端 2 例（metrics/compare）+ API；前端全量。
**验收标准**: 后端 20 通过；前端 608 通过。
