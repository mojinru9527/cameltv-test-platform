# Batch 282（M1 / TA-008）— QA Report

> **部门**：🔍 QA · **日期**：2026-11-10

| # | 标准 | 结果 | 证据 |
|---|------|:----:|------|
| A1 | 列表/详情项目隔离 | ✅ | `test_list_runs` / `test_cross_project_run_is_404` |
| A2 | 事件 `after_seq` + `last_seq` | ✅ | `test_run_detail_events_artifacts` / `test_event...` |
| A3 | Artifact 列表 | ✅ | 同上 + `/artifacts` 端点 |
| A4 | SSE 事件流 | ✅ | `test_sse_once_stream`（content-type + data） |
| A5 | 前端 typecheck/build/lint | ✅ | 0/0/0 |
| A6 | 前端全量测试 | ✅ | 550 passed（123 files） |
| A7 | 后端全量 + ratchet | ✅ | 1398 passed / 43 skipped；PASS |
| A8 | 路由守卫 | ✅ | route inventory 322；路由层禁 ORM 通过 |

## 前端治理专项

| 问题 | 处理 |
|------|------|
| Batch 54 固定色板/灰面测试 2 条失败 | 移除 `text-red-600/emerald/amber/slate/sky`，改用 `text-destructive`/默认 |
| 路由新增导致后端 inventory 漂移 | fixture +5（317→322） |
| 路由直查 ORM 触发守卫 | 查询迁到 `run_query_service` |

## 缺陷

| # | 现象 | 根因 | 修复 |
|---|------|------|------|
| 1 | route inventory 失败 | 新增 5 端点 | 更新基线 |
| 2 | route layer ORM ban 失败 | 路由里 `select/db.get` | 抽 service |
| 3 | 前端 2 条治理测试失败 | 固定 Tailwind 色板 | 语义 token |

## 风险

- SSE 为 30s 短连接 + 轮询兜底，M2 接 outbox/Redis 后再长连接；
- 未做浏览器 E2E（无真实 Run 数据），M2 接入 DAG 后补 Playwright 验收。

## 判定

A1–A8 全绿，建议 Leader APPROVED，M1 可收口。
