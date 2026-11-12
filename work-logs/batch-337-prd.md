# Batch 337（P1-2：Execution Profile / Workflow 审批页面）— PRD / Design / Dev

> mode: **full**（新增 API 接口）· 分支：`feature/batch-337-profile-workflow` · 基线：`origin/main 03f778798`
> 排期来源：`session-a7cc2999` P1 拆批表（batch-337 Profile / Workflow 审批页面）

## 1. 背景

batch-330 只交付了 Profile **列表** API；Workflow 定义一直只有服务层（`workflow_service`），没有任何
HTTP 接口，前端也没有审批入口。结果是：

- Execution Profile 只能靠脚本创建，approved 冻结在 UI 上不可见；
- Workflow 的 approval / checksum / graph 无法被 QA 或管理员查看与审批，M2 的"审批冻结"契约缺少操作面。

## 2. 目标与非目标

**目标**

1. 新增 `/api/v1/aiqe/workflows`：列表（审批状态过滤 + 分页）、详情（含 graph）、审批；
2. 扩展 `/api/v1/aiqe/admin/profiles`：创建、审批、更新 config（approved 后 409 冻结）；
3. 前端新增 `/aiqe/profiles`、`/aiqe/workflows` 两页，共用 `menu:aiqe_runs` 路由守卫；
4. Console 页签（执行记录 / Profiles / Workflow 审批）贯通三个页面；
5. 审批后 UI 显示"已冻结/已通过"，编辑与再次修改被后端拒绝。

**非目标**

- 不实现 Workflow 图编辑器 / 新建 version 流程（A3 planner 负责创建）；
- 不改 Workflow/Profile 数据模型与迁移；
- 不做批量审批与审计导出。

## 3. 设计

| 层 | 变更 |
|----|------|
| 服务层 | `workflow_service` 增加 `list_workflows`（项目隔离 + 状态过滤）与 `get_workflow_for_project` |
| API | 新文件 `api/v1/aiqe_workflows.py`；Profile 写接口并入 `aiqe_admin.py` |
| 权限 | 全部要求 `menu:aiqe_runs`（执行中心）；写/审批叠加 `defect:update` |
| 冻结 | `approval_status=approved` → `frozen=true`；Profile `update_config` 抛 `ProfileError` → HTTP 409 |
| 前端 | `api/aiqeConsole.ts`；`pages/aiqe/{ConsoleTabs,profiles,workflows}.tsx` |
| 路由 | `/aiqe/profiles`、`/aiqe/workflows` 包 `RequirePermission code="menu:aiqe_runs"` |

**错误码**：Workflow 不存在/跨项目 → 404；Profile purpose 非法 → 400；approved 后改 config → 409。

## 4. 实现清单

后端：

- `app/aiqe/services/workflow_service.py`：`list_workflows` + `get_workflow_for_project`。
- `app/api/v1/aiqe_workflows.py`（新）：`GET ""`、`GET /{id}`、`POST /{id}/approve`。
- `app/api/v1/aiqe_admin.py`：`POST /profiles`、`POST /profiles/{id}/approve`、`PATCH /profiles/{id}`，列表响应补 `frozen/owner_id`。
- `app/api/v1/router.py`：注册 workflows router。
- `tests/test_aiqe_workflow_api.py`：8 条（列表/详情/审批幂等/项目隔离/权限/Profile 创建审批冻结/非法 purpose/审批前可改）。

前端：

- `src/api/aiqeConsole.ts`：Profile / Workflow 类型与 API。
- `src/pages/aiqe/ConsoleTabs.tsx`：三页签导航。
- `src/pages/aiqe/profiles.tsx`：列表 + 创建 + 审批 + 冻结徽标。
- `src/pages/aiqe/workflows.tsx`：状态过滤 + 列表 + 详情 Dialog（graph JSON）+ 审批。
- `src/pages/runs/{index,detail}.tsx`：挂载 ConsoleTabs。
- `src/pages/aiqe/__tests__/profiles.test.tsx`：3 条组件测试。

## 5. 风险

| 风险 | 等级 | 处置 |
|------|:----:|------|
| 审批权限过宽（任何 tester 可批） | 中 | 本批沿用 `defect:update`；独立审批权限点列入后续（M9 收口登记） |
| approved 并发审批重复写 | 低 | `approve_workflow` 幂等；approved 直接返回 |
| 页面与 batch-336 路由/守卫冲突 | 低 | 337 基于 336 合入后的 main 合并，冲突在合并时解决 |

## 6. 验收

| # | 标准 | 证据 |
|---|------|------|
| A1 | Workflow 列表/详情含节点数与 graph | `test_list_workflows_*` / `test_workflow_detail_returns_graph` |
| A2 | 审批 approved 且幂等，approved_by/checksum 落库 | `test_approve_workflow_freezes_and_is_idempotent` |
| A3 | 项目隔离（跨项目 404） | `test_workflow_project_isolation` |
| A4 | 无 `menu:aiqe_runs` → 403 | `test_workflows_require_console_permission` |
| A5 | Profile 创建/审批/冻结（409） | `test_create_and_approve_profile` 等 3 条 |
| A6 | 前端列表、审批、创建、冻结禁用 | `profiles.test.tsx` 3 条 |
