# Batch 342（M9-3：Workflow 写 API + 独立审批权限点）— PRD / Design / Dev

> mode: **full**（新接口 + 权限模型变更）· 分支：`feature/batch-342-workflow-write` · 基线：`origin/main 80b28a01d`

## 1. 背景

- batch-337 只提供 Workflow 只读 + 审批；创建/编辑依赖 A3 planner 服务层，Console 无法补图；
- 审批复用 `defect:update`，任何能改缺陷的 tester 都能审批 Workflow，权限粒度过粗；
- TC-AIQE 的"契约/图变更"无法通过 API 完成。

## 2. 目标

1. `POST /api/v1/aiqe/workflows`：校验（schema/nodes/driver/依赖/环/断言）后创建，返回 checksum；
2. `PATCH /api/v1/aiqe/workflows/{id}`：更新 graph；approved → 409（服务层冻结）；
3. 新权限 `aiqe:workflow:approve`（button）：审批端点专用；默认只有管理员（`*`）拥有；
4. 创建/编辑仍要求 `menu:aiqe_runs` + `defect:update`；审批要求 `menu:aiqe_runs` + `aiqe:workflow:approve`。

## 3. 设计

| 点 | 实现 |
|----|------|
| 校验 | `validate_workflow(graph, registered_drivers=DEFAULT_DRIVERS, registered_capabilities=known_capabilities())`，聚合 400 |
| 创建 | `workflow_service.create_workflow`（version 自增、checksum） |
| 编辑 | `update_graph`；`WorkflowImmutableError` → 409 |
| 审批权限 | seed `_ACTIONS` 新增 `aiqe:workflow:approve`；未加入 `_TESTER_ACTIONS`（默认管理员） |
| 路由 | 已有文件追加 POST/PATCH，保持路由层无 ORM |

## 4. 验收

| # | 标准 | 证据 |
|---|------|------|
| A1 | 合法 graph 创建成功（version=1、64 位 checksum） | `test_create_workflow` |
| A2 | 空 nodes → 400 | `test_create_invalid_graph_rejected` |
| A3 | PATCH 更新 checksum | `test_patch_updates_checksum` |
| A4 | 无 `aiqe:workflow:approve` → 403 | `test_approve_requires_dedicated_permission` |
| A5 | 审批后 PATCH → 409；未知 → 404 | 2 条 |
| A6 | 无 `menu:aiqe_runs` → 403；既有 337 审批测试同步授权 | `test_write_requires_console_menu` |

## 5. 风险

| 风险 | 等级 | 处置 |
|------|:----:|------|
| 现有 tester 无法审批（行为变化） | 中 | 符合"审批与编辑解耦"目标；如需委托由管理员在角色中授权 |
| 校验过严阻断 A3 产物 | 低 | 与 planner 使用同一 validator + 相同 capability 集 |
| 存量测试使用旧审批权限 | 低 | 已同步授予测试用户（仅测试夹具） |
