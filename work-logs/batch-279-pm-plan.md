# Batch 279（M1 / TA-005）— PM 计划

> **部门**：🟩 PM · **日期**：2026-11-10

## 1. 里程碑

M1 共 4 批：279（Run 模型）→ 280（Event/Outbox）→ 281（Artifact）→ 282（Console MVP）。

本批只交付 279，且必须**先合入主干**，280 从最新 main 切出（AGENTS 2.1.1）。

## 2. WBS

| # | 工作项 | 产出 | 状态 |
|---|--------|------|:----:|
| 1 | 模型设计（4 表 + 关系 + 索引） | `app/aiqe/models/run.py` | ✅ |
| 2 | 状态机单入口 | `app/aiqe/services/run_state.py` | ✅ |
| 3 | Alembic 迁移 | `20261111_ta005_run_models.py` | ✅ |
| 4 | 模型注册 | `app/models/__init__.py` | ✅ |
| 5 | 单测（状态机 + ORM） | 37 tests | ✅ |
| 6 | 全量回归 + ratchet | CI/本地 | ✅ |
| 7 | 文档/证据/看板 | 本目录 | ✅ |

## 3. 依赖

| 依赖 | 状态 |
|------|------|
| M0 P0-1..5 | ✅ 2026-11-09 PASS |
| 生产 104 表 DROP | ✅ 已执行（94 表） |
| `execution_jobs`（旧派发） | ✅ 存在 |
| `sys_project / sys_user / environment / test_scenarios` | ✅ 存在（INT 主键） |

## 4. 排期

计划 1.5 人日；实际约 3 小时（含迁移兼容性排查）。风险主要在旧表同名与初始 create_all，
已在设计决策中固化。

## 5. 验收与放行

- QA 报告 A1–A7 全绿；
- Leader APPROVED；
- PR required checks 全绿 → squash 合入 main；
- 合入后才允许启动 batch-280。
