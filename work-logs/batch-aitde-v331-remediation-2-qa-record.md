# batch-aitde-v331-remediation-2 — QA 记录

> **QA 记录** | 2026-08-29 | Executor: claude (direct task) | Verdict: PASS
> 分支 `fix/aitde-v331-remediation-2`（基线 main @ da67b867）→ main

## 1. 验证范围

修复 v3.3.1 查漏补缺批次（PR #354）之后仍遗留的验收基建与体验缺口：
C1 e2e 冒烟、C2 Golden AI fixtures、C3 组件测试、B2 AI Debug Drawer、
B4 409 STALE + a11y、B3 TanStack Query、Shadow Mode ≥100 Run 对比 + 审计基线、
audit-ai-pr.ps1 UTF-8 修复。

## 2. 结果总表

| 门禁/测试 | 命令 | 结果 |
|---|---|---|
| 提交卫生 | `pwsh scripts/git/scan-common-bugs.ps1` | HARD=0（WARN 300 为历史基线） |
| 机械门禁 | `pwsh scripts/git/dev-gate.ps1` | GATE_RESULT=PASS_WITH_WARN（G0–G2 全过） |
| 后端硬门禁 | `python -m ruff check app/ --select F821` | All checks passed |
| 后端全量 | `python -m pytest -q` | **1984 passed, 0 failed**（5 个 lanhu 失败系 submodule 未检出，`git submodule update --init lanhu-mcp` 后 40/40 过，无新增失败） |
| 前端类型 | `npm run typecheck` | 通过 |
| 前端 lint | `npm run lint` | 通过（0 warning） |
| 前端全量 | `npx vitest run --maxWorkers=2` | **126 files / 554 tests passed**（默认并发下出现间歇性 JS heap OOM，非代码失败；限并发后全绿。基线 542 + 本批 12） |
| 前端构建 | `npm run build` | ✓ built in 9.7s |
| e2e 冒烟 | `npx playwright test e2e/aitde-v3-*.spec.ts` | **7/7 passed**（真实前后端 :8341/:5441，AITDE flag 开启） |
| 路由基线 | `pytest tests/test_route_inventory.py` | 508 路由一致（新增 GET /api/v2/ai-operations 已登记） |

## 3. Shadow Mode 执行证据（V31 §93 / 99_Cross_Version §4）

- **120/120 Run 对比成立**：AGREE_PASS=80、AGREE_FAIL=40、FALSE_PASS=0、
  RECLASSIFIED=0、UNLINKED=0。
- 执行方式为**真实执行链路**：120 条真实 API 用例经 `api_task_worker.execute_task`
  对注册为项目测试环境的 mock 目标发起真实 HTTP（通过 SSRF host allowlist），
  legacy item 与统一 Run 均由生产代码产出，统一 Outcome 由
  EvidenceCompletenessPolicy + OutcomeClassifier 冻结。
- **审计基线**：120 条 `shadow_audit_feedback`（append-only，AI 执行器预审，
  全部 CONFIRMED；FALSE_PASS 候选为空）。**人工复核未执行**——按 §94 需人工
  reviewer 记录 reviewer/环境/时间/Evidence 后方可勾选人工审计门禁项。
- 证据文件：`test-platform-v2/work-logs/evidence/batch-aitde-v331-remediation-2/
  shadow-compare-report.json|md`；工具：`backend/scripts/shadow_compare_legacy_runs.py`。

## 4. e2e 执行记录（C1）

- 环境：backend `AITDE_V3_ENABLED=true`（:8341）+ vite `VITE_AITDE_V3_ENABLED=true`（:5441）。
- 7/7 通过：missions 列表/新建 Mission 两步→概览/AI 调试入口权限渲染、
  Run 详情统一结论徽章、Replay manifest 时间线、数据源与 Fixture 页可达。
- e2e 发现并修复缺陷：AI 调试入口此前直接 `permissions.includes(code)`，
  对 `['*']` 超级权限账号不可见；入口与 Drawer 统一改用 auth store `hasPerm`。

## 5. 基线失败说明

- 后端：lanhu 5 项失败均为 `lanhu-mcp` submodule 未检出（环境问题，init 后全过）。
- 前端：全量默认并发在 16GB 级 Windows 机器上间歇性 OOM（vitest fork pool）；
  `--maxWorkers=2` 后全绿，与代码无关。

## 6. 遗留与移交

- §93「人工审计 ≥30 PASS + ≥30 失败分类」待人工 reviewer 执行（基线/工作清单已就绪）。
- UI（UiTestRun）侧 Shadow 对比需真实 Playwright 目标环境，未执行。
- e2e 尚未接入 CI（与既有 smoke.spec 同为本地前置脚本模式，如需 CI 化可复用
  responsive-e2e.yml 的启动模式）。
