# Batch 219 — PM Plan
> **PM (🟨)** | Date: 2026-09-03 | Executor: Codex | 完整批次

## 规格摘要
**原始需求**: B9 放行页（覆盖/通过率/风险）+ 绑定 release_bundle + 报告/通知；产出可分享放行证据包。

## 开发任务
### [ ] Task 1: 放行 service（证据包 + 绑定发布包 + 通知）
**描述**: `build_release_package(db, task_id)`（coverage/pass_rate/risk/defects/release_bundle_id）；`release_task(db, task_id, verdict, release_bundle_id, risk, summary)`（校验 verdict/status，task→released）；`notify_release`（NotificationLog）。
**验收标准**: 非法 verdict/status 抛 APIException；绑定 release_bundle；状态→released。
**涉及文件**: `app/services/version_task_service.py`

### [ ] Task 2: API + schemas + route_inventory
**描述**: `GET /version-tasks/{id}/release-package`、`POST /version-tasks/{id}/release`、`POST /version-tasks/{id}/notify`；ReleaseRequest；route_inventory 627。
**验收标准**: 路由守卫绿。
**涉及文件**: `app/api/v1/version_task.py`、`app/schemas/version_task.py`、`tests/fixtures/route_inventory.json`

### [ ] Task 3: 前端放行卡片
**描述**: `src/api/versionTask.ts` 增 buildReleasePackage/releaseTask/notifyRelease；`[taskId].tsx` 增放行卡片（通过率/风险/结论 + 放行/有条件/打回 + 发布包 ID + 通知）。
**验收标准**: typecheck/lint/build/vitest 绿；batch54 语义守卫绿。
**涉及文件**: `src/api/versionTask.ts`、`src/pages/version-tasks/[taskId].tsx`

### [ ] Task 4: 测试
**描述**: 后端 tests/test_version_task.py 增 2 例（release API + illegal verdict）；前端全量。
**验收标准**: 后端 13 通过；前端 608 通过。
**涉及文件**: `tests/test_version_task.py`

## 质量要求
- [x] OpenAPI 同步 — 3 新路由入 route_inventory
- [ ] 单元测试 — 后端 13 + 前端全量
- [ ] 无 console 报错 — sonner toast
