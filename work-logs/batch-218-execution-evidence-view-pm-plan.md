# Batch 218 — PM Plan
> **PM (🟨)** | Date: 2026-09-05 | Executor: Codex | 完整批次

## 规格摘要
**原始需求**: B8 一键运行 + 进度 + 证据回放 + 失败四分类→缺陷草稿。
**目标时间**: 一键跑完；失败四分类正确；证据可回放。

## 开发任务
### [ ] Task 1: version_task_run 模型 + 迁移
**描述**: `app/models/version_task_run.py`（status/progress/total/passed/failed/skipped/blocked/evidence/failures/started_at/finished_at）+ `VersionTask.runs` + `alembic/versions/20260907_version_task_run.py`（chained B7 head）。
**验收标准**: `import app.main` 成功；alembic 单头；drill 通过。
**涉及文件**: `app/models/version_task_run.py`、`app/models/version_task.py`、`app/models/__init__.py`、`alembic/versions/20260907_version_task_run.py`

### [ ] Task 2: run + 覆盖回写 + 失败分类 + 缺陷草稿 service
**描述**: `start_run`（跑已采纳方案条目，回写 progress/coverage/evidence/failures，task 状态→executed）；`list_runs/get_run`；`create_defect_draft`（失败→Defect + version_task_defect）。
**验收标准**: run 计数正确；coverage 回写；失败分类 kind 正确；缺陷草稿生成。
**涉及文件**: `app/services/version_task_service.py`

### [ ] Task 3: API + route_inventory
**描述**: `POST /version-tasks/{id}/run`、`GET /version-tasks/{id}/runs`、`GET /version-tasks/{id}/runs/{run_id}`、`POST /version-tasks/{id}/runs/{run_id}/defect/{failure_index}`；schemas VersionTaskRunOut；route_inventory 624 条。
**验收标准**: 路由层守卫绿；import ok。
**涉及文件**: `app/api/v1/version_task.py`、`app/schemas/version_task.py`、`tests/fixtures/route_inventory.json`

### [ ] Task 4: 前端详情页
**描述**: `src/api/versionTask.ts` 增 startRun/listRuns/createDefectDraft；`src/pages/version-tasks/[taskId].tsx`（运行按钮 + Progress + 覆盖 + 证据回放 + 失败转缺陷）；路由 `/version-tasks/:taskId`。
**验收标准**: typecheck/lint/build 绿；batch54 语义守卫绿。
**涉及文件**: `src/api/versionTask.ts`、`src/pages/version-tasks/[taskId].tsx`、`src/router/index.tsx`

### [ ] Task 5: 测试
**描述**: 后端 tests/test_version_task.py 增 3 例（run/defect/API）；前端 vitest 全量回归。
**验收标准**: 后端 11 通过；前端 608 通过。
**涉及文件**: `tests/test_version_task.py`

## 质量要求
- [x] 响应式 — 详情页流式
- [x] OpenAPI 同步 — 4 新路由入 route_inventory
- [ ] 单元测试覆盖 — 后端 11 + 前端全量
- [x] 无障碍 — @/ui 语义组件
- [ ] 无 console 报错 — sonner toast
