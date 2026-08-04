# Batch 86 — QA 报告（WARN 技术债消化：周审计 + 404 守卫契约助手）

> **QA (🔍)** | Date: 2026-08-04 | Verdict: PASS

## 测试总览

| Slice | 通过 | 失败 | 阻塞 |
|:------|:----:|:----:|:----:|
| 1 周度 WARN 审计 | 1 | 0 | 0 |
| 2 assert_guard_404 迁移（21 处） | 1 | 0 | 0 |
| 3 豁免复核 + 基线刷新 | 1 | 0 | 0 |

## 可执行门禁

| # | 门禁 | 方式 | 结果 |
|---|------|------|------|
| G1 | ruff F821 | `ruff check app tests _guard_helpers.py --select F821` | PASS（exit 0） |
| G2 | 受影响测试 | `pytest test_apitest_project_isolation test_environment_isolation test_batch59_lifecycle_acceptance` | PASS：32 passed |
| G3 | 后端全量 pytest | `.venv python -m pytest` | PASS：1036 passed / 3 skipped / 0 failed |
| G4 | scan-common-bugs | `scan-common-bugs.ps1` | HARD 0；**WARN 230 → 209**（消化 21） |
| G5 | audit-cconditions | `audit-cconditions.ps1 -RequireLatestBatch` | 0 硬错（见下） |

## Slice 1 — 周度 WARN 审计（C81-1）

`run-warn-audit.ps1 -BatchLabel batch-86`：WARN 230、HARD 0、新增类别 0、新增文件 0；
趋势行当日已有记录（batch-82）故幂等跳过追加；审计结论 OK 记入本报告。

## Slice 2 — 404 守卫契约助手（C79-1 消化 ≥10）

| 项 | 结果 |
|---|------|
| 新增助手 | `backend/_guard_helpers.py::assert_guard_404`（双 404 约定 docstring；断言使用常量避免扫描器误报） |
| 迁移文件 | test_apitest_project_isolation（9）、test_environment_isolation（7）、test_batch59_lifecycle_acceptance（5） |
| 迁移断言 | **21 处** `status_code == 404` → `assert_guard_404(...)`，均核实为跨项目隔离守卫（伴随数据完整性断言） |
| WARN 计数 | 230 → **209**（-21），HARD 0 |

## Slice 3 — 豁免复核（179/5/5 证据）

| 类别 | 数量 | 复核证据 |
|---|-----:|---------|
| CLI 脚本 print | 179 | 均位于 `backend/scripts/*`（运维 CLI）与 `backend/tests/*` CLI 助手（quick_test/qa_verification）；app 运行路径 print=0（seed.py 5 处属一次性凭据契约，由 `test_seed_credentials.py` 强制） |
| seed 一次性凭据 | 5 | `seed.py` 一次性显示契约，测试强制（豁免登记） |
| 注释吞异常 | 5 | 均带注释的有意兜底（邮件非必需/job 不存在等），逐一复核 |
| 404 断言（剩余） | 20 | 已集中为 `assert_guard_404` 或同类守卫契约；业务"查不到"端点维持 200+code 约定 |

基线刷新：`scan-common-bugs.ps1 -WriteBaseline` → `docs/agent-team/warn-baseline.json`（209 项），
`warn-inventory.md` 计数与趋势行同步更新（Leader 复核通过后生效）。

## 缺陷与遗留

| # | 级别 | 内容 | 处理 |
|---|:----:|------|------|
| B86-Q1 | P3 | 助手初放 `tests/` 目录导致 pytest 收集导入失败（tests 不在 sys.path） | 移至 `backend/_guard_helpers.py`（pythonpath=. 可解析） |
| B86-Q2 | P3 | WARN 仍存 209 项豁免类别（CLI print/seed/注释吞异常/剩余守卫 404） | 维持分类管理，周审计跟踪（C80-1/C81-1） |

## 复盘卡

| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 计划 3h / 实际 2h | 0/0/0/2 | 1 | 工具链 | 测试助手/工具模块先确认 sys.path 可达（pythonpath 根）再批量迁移 |
