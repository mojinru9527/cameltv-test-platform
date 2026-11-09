# Batch 277b-1 — P0-4 `/uitest` 节点化：Dev 执行记录

> **部门**：🟩 Dev
> **日期**：2026-11-09
> **基线**：`origin/main @ 0fbd420fb`

---

## 1. 改动清单

| 文件 | 改动 |
|------|------|
| `app/models/ui_test.py` | `UiTestRun.execution_job_id`（nullable, index） |
| `alembic/versions/20261110_b277b_ui_run_exec_job.py` | add column + index；downgrade batch drop（可逆） |
| `app/core/config.py` | `uitest_execution_mode`（local/node，默认 local）、`uitest_node_timeout_seconds` |
| `app/services/ui_job_dispatch.py`（新） | `build_payload`（spec + guard + env）、`dispatch`、`sync_run_from_job` |
| `app/services/ui_test_service.py` | `trigger_job` node 分支（不检查控制面 Playwright、不本地入队） |
| `app/services/ui_runner_queue.py` | 恢复 pending 时排除 `execution_job_id != NULL` 的节点任务 |
| `app/services/execution_job_service.py` | `JOB_KINDS += "ui"`；`report()` 后投影 UiTestRun |
| `scripts/node/cameltv_node/executor.py` | `run_spec_files`（写 spec → npx playwright test → 解析 report） |
| `scripts/node/cameltv_node/cli.py` | `kind == "ui"` 且 `mode == "spec"` 走 `run_spec_files` |
| `scripts/node/README.md` | 记录 node 模式与前置条件 |
| `docs/platform-refactor/13-...-spec.md` | §0 P0-4 状态回写 |
| `tests/test_b277b_ui_node_dispatch.py`（新） | 12 条单测 |

---

## 2. 关键实现

### 2.1 派发（控制面）

```python
payload = ui_job_dispatch.build_payload(db, job, project_id=..., base_url=...)
# 读 spec → spec_guard.assert_spec_safe → env slot → payload(mode="spec")
run = UiTestRun(status="pending", ...)
exec_job = ui_job_dispatch.dispatch(db, job, run, project_id=..., payload=payload)
# ExecutionJob(kind="ui")，run.execution_job_id 回填
```

### 2.2 投影（节点上报后）

`execution_job_service.report()` → `sync_run_from_job()`：
状态映射（completed/failed/cancelled → done/fail/cancelled）、result/error/finished_at、
`artifact_dir = evidence_store.bundle_dir(job_id, attempt)`、`writeback_case_result()`。

### 2.3 节点执行器

`run_spec_files()`：文件名白名单校验 → 写 spec → `npx playwright test <spec> --output <evidence>/test-results`
→ 读 `PLAYWRIGHT_JSON_OUTPUT_NAME` 报告 → 拍平 suites/specs/tests。

---

## 3. 验证记录

| 检查 | 命令 | 结果 |
|------|------|------|
| 新增单测 | `pytest tests/test_b277b_ui_node_dispatch.py` | ✅ 12 passed |
| 相关回归 | ui_schedule / playwright_executor / artifact_isolation / runner_profile / prod_guard / timezone / batch258 | ✅ 90 passed |
| 全量后端 | `pytest -q` | ✅ **1332 passed / 43 skipped / 0 failed**（174s） |
| 迁移 | `upgrade head → downgrade -1 → upgrade head` | ✅ 全 0；列存在性符合预期 |
| 质量 ratchet | `quality_ratchet.py` | ✅ increased_keys=0（ruff 768→400 / mypy 193→89） |
| app 导入 | `from app.main import app` | ✅（路由不变） |
| P0 守卫 | `check-p0-ready.ps1` | ⚠️ P0-4 仍红（Dockerfile 未改，属 277b-2） |

---

## 4. 偏差与遗留

| 项 | 说明 |
|----|------|
| 默认未切 node | 无真实节点验收；且 `xhr_capture_service` / playground 仍本地起 Chromium，需 277b-2 一并决策 |
| Dockerfile 未动 | 切默认前不动，避免打断现行 `/uitest` |
| 未跑真实节点 E2E | 本环境无 Playwright/节点；277b-2 在测试环境执行 |
| `execution_jobs.kind` 枚举 | 服务常量加 `"ui"`；DB 列是字符串，无需迁移 |
