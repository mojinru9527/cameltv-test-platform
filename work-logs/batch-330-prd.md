# Batch 330（P1）— AIQE Console 管理 API：PRD

> 模式：完整 · 分支：feature/batch-330-p1-console-api · 基线：`447b2f6de`

## 目标

1. `POST /aiqe/admin/quality-gate`：P0 门禁判定；
2. 噪音规则 CRUD + 续期；
3. `POST /aiqe/admin/artifacts/gc`：30 天留存清理；
4. `GET /aiqe/admin/profiles`：Profile 列表；
5. 路由基线 323 → 330。

## 验收

| # | 标准 | 证据 |
|---|------|------|
| A1 | 质量门禁 API | OpenAPI + route inventory |
| A2 | 规则 CRUD/续期 | 复用 `noise_rule_service`（已有 8 单测） |
| A3 | Artifact GC | 复用 `artifact_gc`（已有 3 单测） |
| A4 | Profile 列表 | 复用 model/query |
| A5 | 路由基线 | `test_route_inventory` PASS（330） |
| A6 | 质量 | ratchet PASS |

## 非目标

- 前端独立页面/菜单（Console UI 后续批次）。
