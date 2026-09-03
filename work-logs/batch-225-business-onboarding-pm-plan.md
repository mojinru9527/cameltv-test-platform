# Batch 225 — PM Plan
> **PM (🟨)** | Date: 2026-09-03 | Executor: Codex | 完整批次

## 开发任务
### Task 1: business_onboarding 模型 + 迁移
**描述**: BusinessOnboarding（name/service_key/api_spec_url/step/version_task_id/baseline）+ alembic/20260909。
**验收标准**: import ok；alembic 单头；drill 通过。

### Task 2: onboarding_service
**描述**: create_onboarding（step1）/complete_step（step2-4：生成 VersionTask+方案、跑基线）/list_onboardings。
**验收标准**: step4 → VersionTask run + baseline + status=active。

### Task 3: API + route_inventory
**描述**: POST/GET /onboarding/businesses + POST /onboarding/businesses/{id}/steps/{step}；route_inventory 639。

### Task 4: 前端向导
**描述**: src/api/versionTask.ts 增 onboarding 函数；src/pages/onboarding/index.tsx（4 步）；路由 /onboarding。

### Task 5: 测试
**描述**: 后端 2 例；前端全量。
**验收标准**: 后端 24 通过；前端 608 通过。
