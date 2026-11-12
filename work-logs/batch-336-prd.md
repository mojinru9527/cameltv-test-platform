# Batch 336（P1-1：执行中心菜单 + `menu:aiqe_runs` RBAC）— PRD / Design / Dev

> mode: **full**（权限模型变更）· 分支：`feature/batch-336-console-menu-rbac` · 基线：`origin/main 03f778798`
> 排期来源：`session-a7cc2999` P1 拆批表（batch-336 Console 菜单 + RBAC）

## 1. 背景

AIQE Run Console 在 batch-282 交付了 `/runs`、`/runs/:runId` 两个页面，batch-330 交付了 Console
管理 API（质量门禁 / 噪音规则 / Artifact GC / Execution Profile），但两者都没有进入 RBAC 菜单模型：

- `/system/menus` 不下发执行中心，侧边栏与命令面板都找不到入口；
- 前端没有路由守卫，任何登录用户都能直达 `/runs`；
- `/api/v1/aiqe/*` 只校验项目隔离，管理 API 复用了 `defect:list/update`，权限语义与"执行中心"不一致。

P1 要求 Console 成为可分配的菜单能力，具备"有权限可见/无权限 403"的完整闭环。

## 2. 目标与非目标

**目标**

1. 菜单种子新增 `menu:aiqe_runs`（名称"执行中心"，路径 `/runs`，sort 24）。
2. 角色默认：`tester` 分配；`viewer`（运营只读）不分配；管理员经 `*` 全量放行。
3. 前端：执行中心进入"结果与缺陷"一级分组；命令面板可搜；`/runs*` 路由守卫，无权限渲染 403。
4. 后端：`/api/v1/aiqe/runs/*` 与 `/api/v1/aiqe/admin/*` 统一要求 `menu:aiqe_runs`；
   写操作继续叠加 `defect:update`，避免只读角色凭菜单权限获得写能力。

**非目标**

- 不改 Run/Event/Artifact 数据模型、SSE 行为（batch-339）；
- 不调整 Console 页面内容与 Profile/Workflow 审批页（batch-337/338）；
- 不新增独立操作权限点。

## 3. 设计

| 层 | 变更 |
|----|------|
| 权限模型 | `Permission(type=menu, code=menu:aiqe_runs)`；seed 幂等 upsert + RolePermission 分配 |
| 菜单树 | `menu_service.menu_tree` 按 `codes` 过滤，无权限不下发（既有机制，无需改） |
| API 门禁 | `require_permission("menu:aiqe_runs")`（内部叠加 `require_project`） |
| 前端守卫 | `RequirePermission`（未登录→/login；无权限→403 页面；`*` 放行） |
| 导航 | `MAIN_ROW_DEFS` "结果与缺陷" = `menu:defect` + `menu:aiqe_runs` |
| 命令面板 | `/runs` 条目 `permission: menu:aiqe_runs` + `menuBacked`（软下线同步隐藏） |

**为什么用菜单权限点而不是新操作点**：仓库既有约定是"菜单 code 即模块准入权限"（`_TESTER_MENUS`
直接写 `menu:*`），`/system/menus` 与 API 共用同一权限点可避免两套口径漂移。

## 4. 实现清单

后端：

- `app/seed.py`：`_MENUS` 新增 `menu:aiqe_runs`；`_TESTER_MENUS` 加入该 code。
- `app/api/v1/aiqe_runs.py`：5 个只读端点改为 `require_permission("menu:aiqe_runs")`。
- `app/api/v1/aiqe_admin.py`：7 个管理端点统一叠加 `menu:aiqe_runs`；写操作保留 `defect:update`。
- `tests/test_aiqe_console_menu.py`：seed 目录、菜单树过滤、API 403/200 共 6 条。

前端：

- `src/layouts/nav-config.ts`：执行中心进入"结果与缺陷"分组。
- `src/router/guard.tsx`：新增 `RequirePermission`；`src/pages/Forbidden.tsx`：403 页面。
- `src/router/index.tsx`：`/runs`、`/runs/:runId` 包守卫。
- `src/components/CommandPalette.tsx`：执行中心条目（权限 + menuBacked）。
- 测试：`router/__tests__/permissionGuard.test.tsx`（4 条）、`nav-config.test.ts`、`CommandPalette.test.ts`。

## 5. 风险

| 风险 | 等级 | 处置 |
|------|:----:|------|
| 存量环境 seed 不重跑导致菜单缺失 | 低 | seed 在启动时幂等执行，RolePermission 用 `_get_or_create` 补齐 |
| 新权限点使既有 AIQE API 调用方 403 | 低 | 生产调用方为管理员 `*`；前端页面同批加守卫 |
| viewer 误获得执行中心 | 低 | 测试断言 `_VIEWER_MENUS` 不含该 code |

## 6. 验收

| # | 标准 | 证据 |
|---|------|------|
| A1 | seed 含 `menu:aiqe_runs` → `/runs`，tester 有、viewer 无 | `test_seed_catalog_contains_aiqe_runs_menu` |
| A2 | 菜单树按权限过滤 | `test_menu_tree_filters_aiqe_runs_by_permission` |
| A3 | 无权限 API 403 / 有权限 200 | 4 条 API 测试 |
| A4 | 无权限路由渲染 403、有权限渲染页面、`*` 放行 | `permissionGuard.test.tsx` |
| A5 | 侧栏/命令面板入口 | `nav-config.test.ts` / `CommandPalette.test.ts` |
