# Batch 248 — QA Report

> **QA (🔍)** | Date: 2026-09-17 | 立场：默认「需要改进」
> 分支：`feature/batch-248-local-ai-agent`（base `becbf5c6`）｜worktree：`F:\CamelTv-worktrees\codex-batch-248-local-ai-agent`

## 1. 结论

**PASS（可进入一次总确认）**。本批交付"平台零推理 + 本地 Agent 闭环"的后端内核、需求域派发、结果导入、CLI 与 AI 任务页；
所有硬门禁与受影响域回归均通过，发现并修复 **1 个 P0（本批自身引入）**、**2 个 P1（存量缺陷，本批顺带修复）**。

## 2. 硬门禁证据

| 门禁 | 命令 | 结果 |
|---|---|---|
| 后端受影响域回归 | `pytest tests -q -k "requirement or ai_"` | **349 passed**, 0 failed（106.78s） |
| 本批新增测试 | `pytest tests/test_ai_local_agent_flow.py -q` | 12 passed |
| 路由基线 | `pytest tests/test_route_inventory.py -q` | passed（基线 663 → **668**，新增 5 条，无删除） |
| 架构守卫 | `pytest test-platform-v2/tests/test_execution_architecture_guard.py -q` | 15 passed（新增 2 条） |
| 静态检查 | `ruff check app/ --select F821` | All checks passed |
| 应用导入 | `python -c "from app.main import app"` | ok |
| 迁移单头 | `alembic heads` | 单头 `20260922_ai_agent_token` |
| 迁移升降级 | 临时 SQLite：`upgrade head → downgrade -1 → upgrade head` | 全部成功（含新增列 `model_name`/`imported_at`） |
| 前端类型 | `npm run typecheck` | passed |
| 前端构建 | `npm run build` | passed（✓ built in 9.37s） |
| 前端依赖安装 | **偏差**：worktree 无 node_modules，采用 junction 复用主仓依赖，未执行 `npm ci` | 记录为已知偏差；PR CI 会执行真实 `npm ci` 兜底 |
| 提交卫生 | `pwsh scripts/git/scan-common-bugs.ps1` | HARD **0**；WARN 332 均为基线（无一条指向本批新文件） |
| CLI 冒烟 | `python scripts/ai_agent/cli.py --help` / `next`（无配置） | 帮助正常；无配置时明确报错并退出码 2 |

## 3. 缺陷清单

### 🔴 P0-1（本批引入，已修复）需求端点 response_model 与旧推理链路不兼容
- **现象**：`POST /requirements/{id}/generate` 在平台内推理分支（`AI_PLATFORM_INFERENCE=true`）返回 `AIGenerateResult` 模型实例，而本批把 response_model 改为 `R[dict]` → `ResponseValidationError`（HTTP 500）。
- **发现方式**：受影响域回归 `tests/test_batch48_requirement_acceptance.py::test_generate_persists_inherited_cases_before_cases_get_and_import` 失败（**不是**测试陈旧，是本批真 bug）。
- **修复**：两条旧链路显式 `.model_dump(by_alias=True)`，返回 JSON 形状与改造前一致（`requirement_ai.py:253`、`requirement_ai_generate.py:261`）。
- **回归**：修复后该文件 27 passed；受影响域 349 passed。

### 🟠 P1-1（存量，已修复）`claim_job` 无项目隔离
- **现象**：`ai_agent_service.claim_job` 只按 `status=pending` 取任务，**未按项目过滤**，任何已注册 Agent 都能认领其他项目的 AI 任务。
- **修复**：按 Agent 的 `project_scope`（或显式 `project_id`）过滤；新增用例 `test_claim_respects_capability_and_project`。

### 🟠 P1-2（存量，已修复）`report_job` 丢弃 `model_name`
- **现象**：Agent 上报的模型名被丢弃，"结果由哪个模型产出"不可追溯。
- **修复**：`ai_jobs.model_name` 落库 + 前端展示；新增用例 `test_report_job_records_model_and_result`。

### 🟡 P2-1（存量，已修复）0 模块"静默确认"
- **现象**：需求拆分在 AI 不可用时返回 0 模块，`extraction/confirm` 仍可把它写成 `confirmed`（2026-09-17 生产核查实证），后续用例生成必然为空且页面无失败提示。
- **修复**：`confirm` 在 `action=confirm` 且 `modules` 为空时返回 `code=400` + 明确文案。

### ⚪ P3-1（已知限制，非缺陷）extract 结果不支持自动导入
- 本批 `POST /ai/jobs/{id}/import` 仅支持 `generate`（用例）类型；`extract` 结果需在需求页人工确认。已在 CLI/文档/UI 中明确提示，登记为下批条件（见 Leader Verdict）。

## 4. 覆盖说明（引用基线 + 新增增量）

- **复用基线**：`test_ai_agent_external.py`（PR-06 外置控制面基线）、`test_execution_architecture_guard.py` 既有 13 条、`test_batch48_requirement_acceptance.py` 既有继承/导入链路。
- **本批新增**：Job 生命周期（创建/列表/详情/隔离）、Agent token 签发/校验/吊销、capability 过滤、stale 回收、上报与模型名、导入幂等、平台开关默认值、派发分支存在性守卫、本地 Agent 控制面不引用平台 LLM 守卫。
- 未执行**全量** `pytest tests`（耗时>20min）；由 PR required checks 在 CI 执行全量兜底，本批已执行受影响域 349 条。

## 5. 复盘卡

| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 计划 8h / 实际约 3h（未含发布） | 1/2/1/1 | 1 | 技术债（存量 claim/model_name/静默确认） | 改 response_model 前先跑一遍受影响域回归，别等宽域回归才发现 |
