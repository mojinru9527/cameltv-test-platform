# Batch 341（M9-2：缺陷修复回归 API，解锁 TC-AIQE-008）— PRD / Design / Dev

> mode: **full**（新接口）· 分支：`feature/batch-341-regression-api` · 基线：`origin/main 7fb0af008`

## 1. 背景

- `defect_regressions` 表与 `POST /defects/{id}/regressions` 已存在（TA-027），但只记录一行"回归请求"，
  不创建新 TestRun，也不回填 `verification_run_id`；
- AIQE Console/API 没有回归入口，TC-AIQE-008（缺陷修复后一键回归）被记为 BLOCKED；
- 旧 Run 必须只读保留，新 Run 需带 `fixed_sha`、`retest_of`。

## 2. 目标

1. `POST /api/v1/aiqe/regressions`：一次调用创建 `verification TestRun`（`source_type=regression`、
   `retest_of=旧 Run`、`commit_sha=fixed_sha`、`status=QUEUED`）+ `defect_regressions` 行并互链；
2. `GET /api/v1/aiqe/regressions` / `GET /{id}`：项目隔离查询；
3. 项目隔离与校验：缺陷/旧 Run 必须属于当前项目，`fixed_sha ≥ 7`；
4. 权限与既有 AIQE 一致：`menu:aiqe_runs` + `defect:list/update`。

## 3. 设计

| 点 | 实现 |
|----|------|
| 服务 | `app/aiqe/services/regression_service.py`：create/get/list + `get_verification_run` |
| Run 事实源 | 新 `TestRun` 行（UUID），`environment_snapshot_json` 记 `fixed_sha/defect_id/previous_run_id` |
| 互链 | `DefectRegression.verification_run_id = run.id`，`run.retest_of = previous_run_id` |
| 旧 Run | 只读引用，不 update |
| 路由 | 新 `api/v1/aiqe_regressions.py`，路由层不碰 ORM（查询走 service） |

## 4. 验收

| # | 标准 | 证据 |
|---|------|------|
| A1 | 创建后新 Run=QUEUED，带 fixed_sha/retest_of，回归行互链 | `test_create_regression_creates_verification_run` |
| A2 | 详情/按缺陷过滤列表 | `test_regression_detail_and_list` |
| A3 | 非法缺陷 400、短 SHA 4xx、跨项目旧 Run 400 | 3 条 |
| A4 | 无 `menu:aiqe_runs` → 403；未知回归 404 | 2 条 |
| A5 | 路由基线同步 | `test_route_inventory` |

## 5. 非目标

- 不自动执行新 Run（执行引擎与调度在 batch-340/343）；
- 不改 `defect_regressions` 表结构。
