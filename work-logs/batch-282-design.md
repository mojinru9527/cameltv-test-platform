# Batch 282（M1 / TA-008）— Design

> **部门**：🟪 Design · **日期**：2026-11-10

## 1. 后端 API（只读）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/aiqe/runs` | 列表：`status/limit/offset`，返回 `items/total` |
| GET | `/api/v1/aiqe/runs/{run_id}` | 详情：run + 最近 200 事件 + artifacts |
| GET | `/api/v1/aiqe/runs/{run_id}/events` | `after_seq/limit`，返回 `items/last_seq` |
| GET | `/api/v1/aiqe/runs/{run_id}/artifacts` | Artifact 列表 |
| GET | `/api/v1/aiqe/runs/{run_id}/events/stream` | SSE：`after_seq`、`once`（测试用） |

全部 `require_project`（`X-Project-Id`），跨项目 404；查询收敛在
`aiqe/services/run_query_service.py`（路由层禁 ORM 守卫通过）。

## 2. SSE 设计

```text
GET .../events/stream?after_seq=N
  → 每轮 list_events(after_seq) → data: <event json>
  → 1s 间隔；30 轮后发送 ": keep-alive" 结束（MVP 短连接）
  → once=1：只推一批后立即结束（测试/首屏）
```

浏览器端 `EventSource` 断线 → 关闭并切 3s 轮询 `GET /events?after_seq=last_seq`，
按 `seq` 去重追加。

## 3. 前端

| 文件 | 职责 |
|------|------|
| `api/aiqeRuns.ts` | 5 个 API 封装（client 拦截器已解 envelope） |
| `types/aiqe.ts` | Run/Event/Artifact 类型 |
| `pages/runs/index.tsx` | 列表（run_key/status/outcome/时间） |
| `pages/runs/detail.tsx` | 详情：指标 + 事件时间线 + Artifact 表 |
| `pages/runs/useRunEvents.ts` | 首拉 + SSE + 断线轮询 + seq 去重 |
| `router/index.tsx` | `/runs`、`/runs/:runId` 懒加载路由 |

样式仅用语义 token（`text-muted-foreground`/`text-destructive`），通过 Batch 54 治理测试。

## 4. 决策

| ID | 决策 | 理由 |
|----|------|------|
| D-282-1 | API 放 `/aiqe/runs` 而非复用 `/ui-tests` | 新域独立演进，避免旧接口语义耦合 |
| D-282-2 | SSE 短连接（30s）+ 前端轮询兜底 | MVP 不引入 Redis PubSub；M2 接 outbox dispatcher |
| D-282-3 | `once=1` 仅测试/调试 | 让 SSE 可被 TestClient 有限读取，避免挂起 |
| D-282-4 | 前端暂不加菜单，URL 直达 | 导航/RBAC 放 M2 统一做 |
| D-282-5 | 路由层禁 ORM | 既有守卫强制；查询全部进 service |
