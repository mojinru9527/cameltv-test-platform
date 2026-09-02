# Batch 213 — PM Plan (home-todo)
> **PM (🟨)** | Date: 2026-09-02

## 规格摘要
**原始需求**: PRD §2/§4 —— 工作台改「我的待办」，四区聚合（待审/在跑/失败/待放行）+ dashboard API；3 分钟说出今天点哪；无埋点。
**目标时间**: 本批（完整前后端）。**范围**: `test-platform-v2/frontend` + `test-platform-v2/backend`。

## 开发任务

### [ ] Task 1: 后端 dashboard/todo 聚合接口
**描述**: 在 `app/api/v1/dashboard.py` 增加 `GET /todo`；在 `dashboard_service` 增加 `get_todo_items(db, project_id)`，聚合四桶，每桶 `{count, items:[{id,title,subtitle,link}]}`（最多 5 条）。新增 Pydantic schema。
**验收标准**:
- `GET /api/v1/dashboard/todo` 返回 `{reviews, running, failures, releases}` 四键，各含 `count` + `items`。
- 待审=`RequirementReview.status='pending'`；在跑=`AiTask.status='running'`；失败=`AiTask.status='failed'` + `Defect.status not in (closed,rejected)`；待放行=`ReleaseBundle.status='active'`。
- 全部按 `project_id=current.project_id` 过滤；空桶返回空 items、count=0。
- 相应 pytest 通过（mock/真实 DB 断言四桶字段）。
**涉及文件**:
- `test-platform-v2/backend/app/api/v1/dashboard.py` — 加 `/todo` 路由
- `test-platform-v2/backend/app/services/dashboard_service.py` — 加 `get_todo_items`
- `test-platform-v2/backend/app/schemas/dashboard.py` — 加 `DashboardTodo*` schema
- `test-platform-v2/backend/tests/.../test_dashboard_todo.py` — 新测试
**参考**: PRD §5 / 现有 `get_dashboard_stats` 分层

### [ ] Task 2: 前端 API + 类型
**描述**: `api/dashboard.ts` 增加 `fetchDashboardTodo(signal)` 调 `/dashboard/todo`；`types` 增加 `DashboardTodo`/`TodoBucket`/`TodoItem` 类型。
**验收标准**: `npm run typecheck` 过；`fetchDashboardTodo` 走 `/dashboard/todo`；无 `any`。
**涉及文件**:
- `test-platform-v2/frontend/src/api/dashboard.ts`
- `test-platform-v2/frontend/src/types/index.ts`（或 `api.d.ts`）
**参考**: PRD §5

### [ ] Task 3: 前端「我的待办」页面
**描述**: 重写 `pages/workbench/index.tsx`：文档标题「我的待办」；用 `useApi` 单次拉 `fetchDashboardTodo`；渲染四区（待审/在跑/失败/待放行），每区显示 count 徽标 + 最多 5 条可点击条目 + 「查看全部」链接；空态教学；loading/error 态；tester 走查「3 分钟说出今天点哪」。
**验收标准**:
- GET `/dashboard/todo` 只出现 1 次有效请求（无 N+1）。
- 四条条目 link 正确（待审→`/requirement/{id}/review`、在跑→需求/AI 任务页、失败→`/defect/{id}`、待放行→`/release-bundles/{id}`）。
- useEffect 含 cleanup（AbortController/取消标志）；无 console 报错。
- 桌面 + 平板断点无水平溢出；空态有教学文案。
**涉及文件**:
- `test-platform-v2/frontend/src/pages/workbench/index.tsx` — 重写
- `test-platform-v2/frontend/src/api/dashboard.ts` / `types` — Task 2
- 可能新增 `components/` 小卡片
**参考**: PRD §4/§5；`cameltv-ui-conventions`

### [ ] Task 4: 首页落地到「我的待办」
**描述**: `router/index.tsx` 的 `PlatformHomeEntry` 默认改 `Navigate to="/workbench"`；保留 `版本验收` 菜单直达 `/missions`。
**验收标准**: 登录后 `/` 落地 `/workbench`（我的待办）；`/missions` 仍可通过菜单/URL 直达；无死循环跳转。
**涉及文件**:
- `test-platform-v2/frontend/src/router/index.tsx`
**参考**: PRD §5 风险决策

### [ ] Task 5: QA + 工件 + 路线图 §5 交接区
**描述**: 跑硬门禁（backend ruff F821 + 相关 pytest + 前端 typecheck/build/vitest）；更新 `routes §5 B3 行`；产出 QA 报告/Leader/看板。
**验收标准**: 门禁全绿；`docs/superpowers/plans/2026-09-02-platform-refactor-rollout.md` B3 行状态更新。
**涉及文件**: work-logs/*.md、kanbans/DEV-batch-213-home-todo.md、rollout.md

## 质量要求
- [x] 响应式（Desktop + Tablet）  - [ ] OpenAPI 同步（`/dashboard/todo`）  - [x] 单元测试覆盖
- [ ] 无障碍（ARIA/键盘）  - [ ] 无 console 报错/告警  - [ ] GET 单次有效请求（Network 验证）
