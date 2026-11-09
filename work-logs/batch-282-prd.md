# Batch 282（M1 / TA-008）— Run Console MVP：PRD

> **部门**：🟦 Product · **日期**：2026-11-10 · **批次模式**：完整
> **分支**：feature/batch-282-m1-run-console · **基线**：origin/main `ad49d9817`

## 1. 问题

Run/Event/Artifact 三层已有事实源，但没有可看的界面，也没有只读 API：
QA 只能查库确认执行进度，无法回放事件或查看证据清单。

## 2. 目标（纵向切片）

1. 只读 API：Run 列表/详情、事件补拉、Artifact 列表、SSE 事件流（`after_seq`、`once` 调试）；
2. 前端 `/runs` 列表与 `/runs/:runId` 详情；
3. `useRunEvents`：首拉 + SSE；断线降级 3s 轮询，按 `seq` 去重；
4. 验收：刷新后状态/事件不丢；Run 可回放；跨项目 404。

## 3. 验收

| # | 标准 | 证据 |
|---|------|------|
| A1 | Run 列表/详情按项目隔离 | `test_list_runs` / `test_cross_project_run_is_404` |
| A2 | 事件 `after_seq` 补拉与 `last_seq` | `test_run_detail_events_artifacts` |
| A3 | Artifact 列表 | 同上 |
| A4 | SSE（once）返回 event-stream 与 data | `test_sse_once_stream` |
| A5 | 前端 typecheck/build 通过 | `tsc -b` / `vite build` |
| A6 | 刷新可回放（首拉 + 去重追加） | `useRunEvents` 实现 + 手工验证 |
| A7 | 全量回归 + ratchet | CI/本地 |

## 4. 非目标

- Run 创建/取消/重跑（M2 DAG API）；
- SSE 多副本广播（Redis PubSub 在 M2 接 outbox dispatcher）；
- 菜单/权限点配置（先用 URL `/runs`，M2 纳入导航与 RBAC）。
