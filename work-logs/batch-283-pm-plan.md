# Batch 283（M2 / TA-009）— PM 计划

> **部门**：🟩 PM · **日期**：2026-11-10

## 里程碑

M2 第 1 批（TA-009）：M1 ✅ → **283（本批）** → TA-010 DAG Scheduler。

## WBS

| # | 工作项 | 产出 | 状态 |
|---|--------|------|:----:|
| 1 | 校验器 | `aiqe/services/workflow_validator.py` | ✅ |
| 2 | 16 条单测 | `tests/test_aiqe_workflow_validator.py` | ✅ |
| 3 | 全量回归 + ratchet | CI/本地 | ✅ |
| 4 | 六件套 + 看板 | work-logs | ✅ |

## 依赖

- M1 收口 ✅（ae13542a3）；
- 生产 M1 迁移已部署（20261113 head，101 表）✅。

## 排期

计划 0.5 人日；实际 ≈ 40min。

## 放行

A1–A8 全绿 → Leader → PR → 合入 → TA-010。
