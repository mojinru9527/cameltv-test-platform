# Batch 217 — PM Plan
> **PM (🟨)** | Date: 2026-09-05 | Executor: Codex | 完整批次

## 规格摘要
**原始需求**: B7 建任务向导（前后端）。3 步：填需求→审方案→确认；审核面板（采纳/改/删/追问+置信度+待确认）；无引擎术语。
**目标时间**: 拖入需求→可审方案→逐条确认。

## 开发任务
### [ ] Task 1: 后端验收方案条目模型 + 迁移
**描述**: `app/models/version_task_plan.py`（item_type/title/description/confidence/status/question/answer/order_index）+ `VersionTask.plan_items` 关系 + `alembic/versions/20260906_version_task_plan_item.py`（chained B6 head）。
**验收标准**: `import app.main` 成功；`alembic heads` 单头；upgrade→downgrade→upgrade 通过。
**涉及文件**: `app/models/version_task_plan.py`、`app/models/version_task.py`、`app/models/__init__.py`、`alembic/versions/20260906_version_task_plan_item.py`

### [ ] Task 2: 方案生成 + 审核 service
**描述**: `version_task_service.generate_plan(db, task_id, items)` 写入方案条目；`review_plan_item(db, item_id, action, patch)` → adopt/modify/remove/ask/confirm。
**验收标准**: 生成 2 条 → adopt/modify/ask/remove 状态正确；非法 action 抛 APIException(code=1)。
**涉及文件**: `app/services/version_task_service.py`

### [ ] Task 3: API + route_inventory
**描述**: `POST /version-tasks/{id}/plan/generate`、`GET /version-tasks/{id}/plan`、`POST /version-tasks/{id}/plan/{item_id}/review`；schemas PlanItemCreate/Review/Out；route_inventory 620 条。
**验收标准**: `import app.main` 成功；route-inventory 绿。
**涉及文件**: `app/api/v1/version_task.py`、`app/schemas/version_task.py`、`tests/fixtures/route_inventory.json`

### [ ] Task 4: 前端 API client + 向导页
**描述**: `src/api/versionTask.ts`；`src/pages/version-tasks/index.tsx`（3 步向导 + 审核面板）；路由 `/version-tasks`。
**验收标准**: typecheck/lint/build 绿；batch54 守卫（无固定色板）绿。
**涉及文件**: `src/api/versionTask.ts`、`src/pages/version-tasks/index.tsx`、`src/router/index.tsx`

### [ ] Task 5: 测试
**描述**: 后端 `tests/test_version_task.py` 增 B7 2 例（service + API）；前端 vitest 全量回归。
**验收标准**: 后端 version_task pytest 8 通过；前端 vitest 608 通过。
**涉及文件**: `tests/test_version_task.py`

## 质量要求
- [x] 响应式（Desktop + Tablet） — 向导卡片流式布局
- [x] OpenAPI 同步 — 新路由入 route_inventory
- [ ] 单元测试覆盖 — 后端 8 + 前端全量
- [x] 无障碍（ARIA/键盘） — 复用 @/ui 语义组件
- [ ] 无 console 报错/告警 — sonner toast 统一
