# Batch 280（M1 / TA-006）— PM 计划

> **部门**：🟩 PM · **日期**：2026-11-10

## 1. 里程碑

M1 第 2 批（共 4）：279 ✅ → **280（本批）** → 281 Artifact → 282 Console。

## 2. WBS

| # | 工作项 | 产出 | 状态 |
|---|--------|------|:----:|
| 1 | 事件/Outbox 模型 | `aiqe/models/event.py` | ✅ |
| 2 | append_event / dispatch / list | `aiqe/services/event_service.py` | ✅ |
| 3 | 迁移 20261112 | `20261112_ta006_run_events.py` | ✅ |
| 4 | 模型注册 | `app/models/__init__.py` | ✅ |
| 5 | 单测 10 | `tests/test_aiqe_event_service.py` | ✅ |
| 6 | 全量回归 + ratchet | 1386 passed / PASS | ✅ |
| 7 | 六件套 + 看板 | work-logs | ✅ |

## 3. 依赖

- batch-279 四表（test_runs/node_runs/step_attempts）✅ 已合入；
- `append_event` 投影回调由后续 DAG/Worker 使用（M2）。

## 4. 排期

计划 1 人日；实际 ≈ 1.5h。风险集中在迁移预建兼容（与 279 同策略，已复用）。

## 5. 放行

A1–A6 全绿 → Leader APPROVED → PR checks → squash 合入 → 切 batch-281。
