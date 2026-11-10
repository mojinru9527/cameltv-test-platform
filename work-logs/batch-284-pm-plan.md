# Batch 284（M2 / TA-010）— PM 计划

> **部门**：🟩 PM · **日期**：2026-11-10

## 里程碑

M2 第 2 批：TA-009 ✅ → **TA-010 / TA-010.3（本批）**。

## WBS

| # | 工作项 | 产出 | 状态 |
|---|--------|------|:----:|
| 1 | WorkflowDefinition / ResourceLock 模型 | `aiqe/models/workflow.py` | ✅ |
| 2 | Workflow 服务（创建/审批/冻结） | `aiqe/services/workflow_service.py` | ✅ |
| 3 | 资源锁（TTL/fencing/续租） | `aiqe/services/resource_lock.py` | ✅ |
| 4 | DAG 调度器（推进/并行/阻断/收口/恢复） | `aiqe/services/dag_scheduler.py` | ✅ |
| 5 | 迁移 20261114 | `20261114_ta010_workflow_scheduler.py` | ✅ |
| 6 | 单测 15 | 3 个测试文件 | ✅ |
| 7 | 全量 + ratchet | 1429 passed / PASS | ✅ |
| 8 | 六件套 + 遗留登记 | work-logs | ✅ |

## 依赖

- batch-283 校验器 ✅；
- M1 `test_runs / node_runs` ✅（生产已迁移 20261113）。

## 排期

计划 1 人日；实际 ≈ 2.5h（含 SQLite 时区与 mypy 修正）。

## 放行

A1–A9 全绿 → Leader → PR → 合入；生产部署随 M2 窗口（新增 2 表）。
