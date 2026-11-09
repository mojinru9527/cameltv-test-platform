# Batch 282（M1 / TA-008）— PM 计划

> **部门**：🟩 PM · **日期**：2026-11-10

## 里程碑

M1 第 4 批（收口）：279 ✅ → 280 ✅ → 281 ✅ → **282（本批）**。

## WBS

| # | 工作项 | 产出 | 状态 |
|---|--------|------|:----:|
| 1 | 只读 API（列表/详情/事件/Artifact/SSE） | `api/v1/aiqe_runs.py` + schema | ✅ |
| 2 | 路由注册 | `router.py` | ✅ |
| 3 | 前端 API/类型 | `api/aiqeRuns.ts`、`types/aiqe.ts` | ✅ |
| 4 | Run List / Detail / useRunEvents | `pages/runs/*` | ✅ |
| 5 | 路由 | `router/index.tsx`（/runs、/runs/:runId） | ✅ |
| 6 | 后端单测 6 + 前端 typecheck/build/test | 见 QA | ✅ |
| 7 | 六件套 + 看板 + M1 收口 | work-logs | ✅ |

## 依赖

- batch-279/280/281 服务与表 ✅；
- `require_project` + `X-Project-Id` 现有鉴权 ✅；
- SSE 端点复用 `list_events`，无需新表。

## 放行

A1–A7 全绿 → Leader APPROVED → PR checks → 合入 → **M1 收口报告**。
