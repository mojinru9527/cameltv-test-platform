# M1 / M2 遗留项登记（2026-11-10）

> 来源：M1 收口（`M1-phase1-closeout.md`）+ M2 前两批（TA-009 / TA-010）复盘。
> 状态：`done` / `partial` / `open` / `decision-needed`。

| # | 来源 | 遗留项 | 状态 | 计划 / 建议 |
|---|------|--------|:----:|-------------|
| 1 | M1 TA-007 | 生产对象存储后端 | **partial（用户选 MinIO）** | 代码已支持（batch-285：MinIO + SigV4 + compose）；生产容器/env/ensure_bucket 待窗口 |
| 2 | M1 TA-008 | Console 菜单/RBAC 入口（`menu:aiqe_runs`） | open | 需权限 seed + 导航；放 M2 后段 UI 批次，当前 URL `/runs` 直达 |
| 3 | M1 TA-008 | SSE 长连接 / Redis PubSub | open | 当前 30s SSE + 轮询兜底；M2 接 outbox dispatcher 后改长连接 |
| 4 | M1 TA-008 | Console 浏览器 E2E | open | 依赖可造 Run 的 DAG 执行链；TA-012/013 后补 Playwright 用例 |
| 5 | M1 TA-007 | Artifact 留存/GC | open | 文件只增不减；建议 30 天 + 按 Run 级联清理，随 M2 运维批次 |
| 6 | M2 TA-009 | 规则 6（写动作 profile policy） | open | 依赖 `execution_profiles` 表；TA-010 后续/TA-011 |
| 7 | M2 TA-009 | 规则 7 审批 API/UI | partial | 存储层冻结已实现（`approve_workflow` / `update_graph` 拒绝）；HTTP API/审批流待补 |
| 8 | M2 TA-010 | 条件边（`edges.condition`） | open | 当前只支持成功边；failure/always 分支随 TA-010 后续 |
| 9 | M2 TA-010 | 调度器接 ExecutionJob / Worker | open | dispatch 目前是回调；TA-012+ 接入真实执行 |
| 10 | M2 TA-015 | capability 注册表 | done | `capability_registry` + 迁移 20261115（生产待窗口） |
| 11 | 部署 | batch-283/284 生产部署 | **done** | 2026-11-11 已部署（20261114，103 表）；M2 代码已 delta 部署，20261115 待窗口 |
| 12 | 运维 | `start-worker.sh` 已在 main（batch-277b-6 修复） | done | — |

## 本轮已顺手处理

- 规则 7 的**存储层冻结**：`workflow_service.approve_workflow()` + `update_graph()`（approved 拒绝）；
- Workflow 校验器已接入 `workflow_definitions.checksum`（审批前后一致）。

## 建议排期

1. **M2 窗口部署**（#11）——低风险，新增 2 表；
2. **Console 菜单 + RBAC**（#2）——独立小批；
3. **TA-011/012/013**（#8/#9 的前置）；
4. 存储选型（#1）与留存（#5）——需业务/运维决策。
