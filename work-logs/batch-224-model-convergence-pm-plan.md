# Batch 224 — PM Plan
> **PM (🟨)** | Date: 2026-09-05 | Executor: Codex | 完整批次

## 开发任务
### Task 1: convergence_service
**描述**: archive_test_plan（status=archived + 绑 VersionTask）；unified_assets_view（single_fact_source=version_task）；merged_data_assets（Dataset 合并）。
**验收标准**: 归档/视图/合并正确。

### Task 2: API + route_inventory
**描述**: GET /convergence/assets、GET /convergence/data-assets、POST /convergence/test-plan/{id}/archive；route_inventory 636。

### Task 3: 测试
**描述**: 后端 2 例 + API。
**验收标准**: 后端 22 通过。
