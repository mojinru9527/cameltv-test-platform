# Batch 224 — Design Spec
> **Design (🎨)** | Date: 2026-09-05 | Status: 就绪 | Executor: Codex | 完整批次

## 0. 技术体系
后端 FastAPI + SQLAlchemy；无前端改动。

## 1. 数据模型
无新表。复用 TestPlan.status（archived）、VersionTask（单一事实源）。

## 2. 接口
- /convergence/assets → single_fact_source=version_task + test_plans/datasets/release_bundles
- /convergence/data-assets → data_assets 数组
- /convergence/test-plan/{id}/archive?version_task_id= → archived

## 3. 设计 QA 走查发现
无。

## 4. 设计签核
结论：**通过**。
