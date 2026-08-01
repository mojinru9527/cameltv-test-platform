# Batch 60 Sports Platform Production Validation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. These sub-skills are not installed in this workspace, so the confirmed Codex Agent Team workflow is the execution fallback.

**Goal:** Deploy the latest main branch as an isolated Batch 60 local platform, validate every reachable platform capability with repository-backed CamelTv sports data wherever possible, record reproducible defects and blockers, and fix accepted findings one by one to production delivery standards.

**Architecture:** Treat the platform as four coupled validation layers: React UI, FastAPI/OpenAPI, SQLite business state and audit evidence, plus external sports systems and tools. A separate operations release control plane binds the production React image, FastAPI image and Alembic target into one immutable release unit and promotes the same digest from test to production. Local R1 data validates complete platform workflows without inventing sports semantics; external Test5/production checks are separate R2/R3 evidence and remain blocked when VPN, credentials, devices, service contracts or production infrastructure are unavailable. Every release conclusion is derived from A01–A14 evidence rather than build status alone.

**Tech Stack:** React 19, TypeScript, Vite 7, Playwright, Vitest, FastAPI, SQLAlchemy 2, SQLite WAL, Pytest, PowerShell, Markdown evidence.

---

### Task 1: Freeze the Batch 60 baseline

**Files:**
- Local metadata: `.ai-worktree.json` (ignored)
- Create: `test-platform-v2/work-logs/batch-60-real-data-manifest.md`

- [x] **Step 1: Fetch the remote baseline**

Run: `git fetch origin --prune`

Expected: `origin/main` resolves to `d15ed2197e41bbcecfac733f059160a912373317`.

- [x] **Step 2: Create the isolated Agent Team worktree**

Run from `F:\CamelTv`:

```powershell
pwsh scripts/git/start-agent-team-task.ps1 `
  -Executor codex -UserConfirmedExecutor `
  -Kind feature `
  -Task batch-60-sports-platform-production-validation `
  -Scope test-platform-v2,tests,docs,work-logs `
  -FrontendPort 5196 -BackendPort 8026
```

Expected: branch `feature/batch-60-sports-platform-production-validation`, ahead/behind `0/0`, clean worktree.

- [x] **Step 3: Verify workflow metadata and isolation**

Run:

```powershell
pwsh scripts/git/verify-ai-worktree.ps1 `
  -RequireClean -RequireMetadata `
  -ExpectedWorkflow agent-team -ExpectedExecutor codex
```

Expected: workflow `agent-team`, executor `codex`, frontend `5196`, backend `8026`, scopes `test-platform-v2`, `tests`, `docs`, `work-logs`.

### Task 2: Deploy the isolated local platform

**Files:**
- Local runtime: `test-platform-v2/config/runtime/local.env` (ignored)
- Local database: `test-platform-v2/backend/data/platform-local.db` (ignored)
- Runtime manifest: `%TEMP%/cameltv-platform-local/runtime-manifest.json` (temporary)

- [x] **Step 1: Install exact frontend dependencies**

Run: `npm ci` from `test-platform-v2/frontend`.

Expected: exit code `0`, zero npm audit vulnerabilities during install.

- [x] **Step 2: Install backend dependencies in an isolated virtual environment**

Run:

```powershell
python -m venv test-platform-v2/backend/.venv
test-platform-v2/backend/.venv/Scripts/python.exe -m pip install -r test-platform-v2/backend/requirements.txt
```

Expected: exit code `0`; `uvicorn`, `pytest`, Playwright and FastAPI import from the worktree virtual environment.

- [x] **Step 3: Generate independent local secrets and bind Batch 60 ports**

Run the repository startup helper with `-InitializeLocal`, then configure the ignored profile for frontend `5196`, backend `8026`, and `platform-local.db`.

Expected: generated secrets never appear in Git, chat, screenshots or QA reports.

- [x] **Step 4: Start and probe the platform**

Verify:

```text
GET http://127.0.0.1:8026/health             -> 200
GET http://localhost:5196/login              -> 200
GET http://localhost:5196/api/v1/open/health -> 200
```

Expected: all three probes return `200`; browser login reaches `/workbench` without console errors or failed responses.

### Task 3: Establish the real-data hierarchy

**Files:**
- Create: `test-platform-v2/work-logs/batch-60-real-data-manifest.md`
- Read: `产品需求/蓝湖原型-用户端原型-20260611_180510.json`
- Read: `产品需求/蓝湖原型-运营后台-20260611_180605.json`
- Read: `tests/requirements/documents/用户端原型-需求分析.md`
- Read: `tests/requirements/documents/运营后台-需求分析.md`
- Read: `tests/test-cases/functional/BASELINE-用户端-基线功能.md`
- Read: `tests/test-cases/functional/ADMIN-运营后台-全版本.md`
- Read: `tests/test-cases/体育平台最新版本-测试用例.md`

- [ ] **Step 1: Classify every input as R1, R2 or R3**

Use these fixed meanings:

```text
R1 = repository-backed sports documents, redacted historical traffic or static contracts
R2 = live Test5/non-production sports endpoints with authorized credentials and VPN
R3 = production read-only GET/HEAD evidence; no payment, publication, ban, load or destructive writes
```

Expected: every executed case cites one source and one data level; mock is permitted only with a written missing-condition reason.

- [ ] **Step 2: Import R1 sports requirements through the UI**

Use unique names beginning `batch60-`. Import the user and admin requirement analyses, preview parsing, confirm modules, and verify API, UI, DB and audit consistency.

Expected: both positive and negative upload cases exist; rejected files produce no requirement, module, task or audit side effects.

- [ ] **Step 3: Import R1 sports test cases and static OpenAPI assets**

Use existing repository files, not generated mock sports data. Validate counts, duplicate imports, invalid formats, project ownership, search, sorting and pagination.

Expected: list totals and persisted rows match the parsed source; duplicate or invalid imports are explicit and reversible.

### Task 4: Build the complete feature and route matrix

**Files:**
- Create: `test-platform-v2/work-logs/batch-60-full-platform-execution-matrix.md`
- Read: `test-platform-v2/frontend/src/router/index.tsx`
- Read: `test-platform-v2/frontend/src/layouts/MainLayout.tsx`
- Read: `test-platform-v2/backend/app/api/v1/router.py`
- Read: `test-platform-v2/backend/app/seed.py`

- [ ] **Step 1: Register all reachable surfaces**

Expected inventory: login, 23 business routes, internal `/theme-lab`, and every `/api/v1` domain including WebSocket/open/playground paths.

- [ ] **Step 2: Add positive and negative cases per feature point**

Each matrix row contains source, priority, identity, project, input, UI action, API assertion, DB/audit assertion, cleanup, evidence, actual result and defect ID.

Expected: every feature point has at least one positive and one negative case before it can be marked covered.

- [ ] **Step 3: Include hidden and direct-only modules**

Directly test `/release-bundles`, `/defect`, `/dataset`, `/integration`, `/notify` and `/environment`; do not treat the visible sidebar as the complete platform.

Expected: route coverage and feature coverage are reported separately.

### Task 5: Execute the platform management and isolation foundation

**Files:**
- Evidence: `test-platform-v2/work-logs/evidence/batch-60-sports-platform-validation/foundation/`

- [ ] **Step 1: Validate login and session lifecycle**

Cover valid login, empty fields, wrong password, disabled user, logout, expired session, refresh, audit record and unauthorized direct routes.

Expected: P0 cases pass with no credential leakage in evidence.

- [ ] **Step 2: Validate project, user, role and token CRUD**

Use administrator, project-scoped tester and no-permission identities across list/detail/subresource/write operations.

Expected: cross-project reads and writes return `403/404` without leaking names, counts or structure.

- [ ] **Step 3: Validate project switching on every project-scoped page**

Open project A state, switch to project B, then verify stale rows, selections, dialogs and pending requests are cleared before any B write can occur.

Expected: exactly one effective GET per resource after switch; no A data is displayed or mutated under the B header.

### Task 6: Execute the sports requirement-to-quality closed loop

**Files:**
- Evidence: `test-platform-v2/work-logs/evidence/batch-60-sports-platform-validation/closed-loop/`

- [ ] **Step 1: Requirement to reviewed case**

Execute document import → preview → module split → confirmation → case generation/review → formal case import using R1 sports documents.

Expected: every resulting case preserves requirement/source traceability.

- [ ] **Step 2: Case to plan and execution**

Create a Batch 60 plan, add/sort/assign cases, execute pass/fail/skip/block, retry, cancel and repeated-submit paths.

Expected: status, counters, execution history, audit log and persisted rows remain transactionally consistent.

- [ ] **Step 3: Failure to defect, report and trace**

Create a defect from a failed execution, traverse the legal state machine, generate a report, and drill through traceability and release-bundle views.

Expected: all pages reference the same requirement, case, execution and defect IDs; broken detail navigation is a failed P0/P1 case.

### Task 7: Execute specialty modules with real capabilities

**Files:**
- Evidence: `test-platform-v2/work-logs/evidence/batch-60-sports-platform-validation/specialty/`

- [ ] **Step 1: API testing**

Import the repository static sports OpenAPI first, bind an R1 environment and dataset, run positive/negative requests, cancel a batch, and verify request/response/assertion snapshots. Test5 stays blocked until its VPN and current contract are authorized and available.

- [ ] **Step 2: UI automation**

Use local locator-based Playwright with credentials kept in process environment. Do not run the existing Midscene sports suite with real credentials until credential prompts and traffic capture are remediated.

- [ ] **Step 3: Audio/video**

Use a repository-backed media sample or an explicitly authorized real stream. Verify async running/completed/failed states, ffprobe metrics, thresholds, duplicate trigger handling and truthful completion feedback.

- [ ] **Step 4: Performance**

Execute validation and failure behavior without inventing devices. Real collection is `BLOCKED` until SoloX plus an authorized Android/iOS device is present.

- [ ] **Step 5: Schedule, notify, integration and open API**

Validate local state machines and negative cases. SMTP, Webhook, Jira/TAPD, ELK and external callbacks remain blocked unless real non-production endpoints and credentials are supplied.

### Task 8: Execute browser, responsive, accessibility and network coverage

**Files:**
- Evidence: `test-platform-v2/work-logs/evidence/batch-60-sports-platform-validation/browser/`
- Create: `test-platform-v2/work-logs/batch-60-pc-usage-snapshot-index.md`
- Evidence: `test-platform-v2/work-logs/evidence/batch-60-sports-platform-validation/pc-usage-snapshots/`

- [ ] **Step 1: Run all routes at desktop, tablet and mobile sizes**

Use `1440×900`, `768×1024` and `390×844` with a visible browser.

Expected: no horizontal overflow, clipped controls, inaccessible dialogs or blocked primary action.

- [ ] **Step 2: Validate keyboard and accessible names**

Check skip link, logical focus, modal focus return, labels, icon-button names, table keyboard behavior and status announcements.

Expected: P0 journeys have a keyboard-equivalent path and WCAG AA labels/contrast.

- [ ] **Step 3: Record network behavior**

Count effective GETs per action, abort superseded requests, and verify search buttons do not issue one request per keystroke.

Expected: one effective GET per intended action, with no N+1 or stale response overwrite.

- [ ] **Step 4: Capture customer-reviewable PC usage snapshots**

At `1440×900`, save a PNG after every successfully exercised feature action and map it to its feature ID, real-data source, project, action, result and test evidence in the snapshot index. Capture meaningful success states such as persisted rows, details, execution output, audit history and exports—not route shells or loading placeholders.

Expected: every function marked `PASS` has at least one redacted PC snapshot; blocked, failed and API-only capabilities remain explicitly without a pass snapshot and cannot be represented by mock or staged UI.

### Task 9: Run local hard gates and full regression

**Files:**
- Create: `test-platform-v2/work-logs/batch-60-qa-report.md`

- [x] **Step 1: Backend hard gate and regression**

Run:

```powershell
test-platform-v2/backend/.venv/Scripts/python.exe -m ruff check test-platform-v2/backend/app --select F821
test-platform-v2/backend/.venv/Scripts/python.exe -m pytest test-platform-v2/backend/tests -q
```

Result: Ruff F821 passed；后端全量 `946 collected，943 passed，0 failed，3 skipped，3 warnings`。skip 均为 PostgreSQL 并发环境用例，结果已写入 QA 报告。

- [x] **Step 2: Frontend hard gate and regression**

Run from `test-platform-v2/frontend`:

```powershell
npm run typecheck
npm test
npm run build
```

Also run lint, coverage and relevant Playwright suites as observational evidence.

Result: `npm run typecheck`、`npm test -- --run`（73 文件/272 测试）和 `npm run build` 全部通过；相关浏览器、可访问性和网络证据仍按问题台账列出。

- [ ] **Step 3: Supply-chain and repository hygiene audit**

Record npm/pip audit results, tracked database/backup artifacts, debug statements and secret scanning.

Result: 仓库 SQLite/`.bak` 制品已移除并补充 ignore，`git diff --check` 通过；体育自动化仍有 7 high，后端 pip-audit 因 advisory 服务超时未取得完整结果，故该步骤保持未完成。

### Task 10: Record, prioritize and fix accepted defects

**Files:**
- Create: `test-platform-v2/work-logs/batch-60-issue-register.md`
- Modify per defect: exact source and test files cited in the issue row

- [ ] **Step 1: Record every failed or blocked case**

Each issue includes ID, severity, module, source case, environment, exact steps/input, expected, actual, impact, evidence, suspected location, status, owner, cleanup and retest scope.

Expected: no issue is represented only by a screenshot or subjective sentence.

- [ ] **Step 2: Fix one issue at a time using a failing test**

For each accepted issue: add the smallest behavior-level failing test, run it to observe the intended failure, implement the smallest fix, rerun the focused test, then rerun the affected P0 workflow.

Expected: every fix maps `issue ID → failing test → commit → focused pass → affected regression pass`.

Batch 60 收尾已补齐并复测的局部映射：`B60-P0-004/B60-P1-019 → test_batch60_api_production_guard.py → 2 passed`；`B60-P1-006 → testcase/index.test.tsx → 1 passed`；`B60-P1-008 → InteractionAnnotator.test.tsx → 2 passed`；`B60-P2-001 → frontend typecheck/full test/build → 73 files/272 tests passed`。其余台账条目仍按状态和外部条件执行。

- [ ] **Step 3: Recompute A01–A12 and the release verdict**

Expected: `READY`, `CONDITIONAL` or `NEEDS WORK` is mechanically derived from evidence; external blockers remain visible and are never relabeled as pass.

### Task 11: Define and phase the operations release platform

**Files:**
- Create: `test-platform-v2/docs/operations/运维发布平台-架构与交付要求.md`
- Read: `docs/adr/0015-operations-release-control-plane.md`
- Modify: `test-platform-v2/work-logs/batch-60-full-platform-execution-matrix.md`
- Modify: `test-platform-v2/docs/改进任务backlog.md`

- [x] **Step 1: Record the release architecture contract**

Define the control/data-plane boundary, immutable release manifest, same-digest test-to-production promotion, frontend/backend/Alembic order, backup, health, rollback, RBAC, approval, audit, Secret references, failure state machine, Jenkins transition and measurable non-functional requirements.

Expected: the architecture document is consistent with ADR-0015 and explicitly records production as `DEFERRED`, not passed.

- [ ] **Step 2: Complete Phase 0 release contracts**

Create a machine-validatable release manifest schema, environment inventory and manual test deployment/rollback runbook. Generate one Batch 60 manifest from the frozen SHA without including a Secret value.

Expected: frontend/backend digests, Alembic target, configuration schema and QA evidence are bound to one release ID; schema validation and a test-only dry run pass.

- [ ] **Step 3: Implement Phase 1 immutable test delivery**

Make Jenkins/Runner consume a release ID and immutable digests, then execute the test environment lock, backup, migration job, backend, frontend, health, business smoke, audit and application rollback flow.

Expected: rebuilding in the production job is impossible; repeated commands are idempotent; a forced failure returns test to the previous compatible application release.

- [ ] **Step 4: Implement Phase 2 control-plane API and UI**

Deliver the release/environment APIs, operations UI, RBAC, explicit approval, event timeline, rollback, notification and Secret Provider integration defined by the architecture contract.

Expected: QA and operations can complete test delivery and a production preflight without SSH or direct database access; permission and state-transition tests pass.

- [ ] **Step 5: Hold Phase 3 until production infrastructure exists**

Do not execute production deployment until the server/cluster, DNS, TLS, PostgreSQL, registry, Secret Manager, monitoring, backup restore and release window are registered and approved.

Expected: current state stays `DEFERRED`; when prerequisites exist, promote the exact test-verified digests and complete a backup-restore drill before declaring `PRODUCTION_VERIFIED`.

- [ ] **Step 6: Evaluate A13 operations release gate**

Verify manifest integrity, same-digest promotion, migration/health/rollback evidence, RBAC/approval/audit, Secret redaction and recovery drill.

Expected: A13 cannot pass from architecture documents alone and cannot be removed from the denominator by labeling production unavailable.

- [ ] **Step 7: Evaluate A14 PC usage snapshot gate**

Cross-check the feature matrix, snapshot index and files. Reject duplicate, empty, loading, error, mock, secret-bearing or unmapped screenshots.

Expected: A14 passes only when every function reported as normally usable has a customer-reviewable PC snapshot and every missing snapshot has a matching failed/blocked/not-run result.

### Task 12: Commit and prepare delivery

**Files:**
- All Batch 60 plan, matrix, issue, QA and approved fix files

- [ ] **Step 1: Review the exact change set**

Run: `git status --short`, `git diff --check`, `git diff --stat`, and inspect every changed file.

Expected: only Batch 60 scope files; no credentials, SQLite/WAL, backups, browser state, node_modules, venv or temporary evidence.

- [ ] **Step 2: Commit coherent batches**

Use small commits such as:

```text
docs: establish Batch 60 production validation baseline
test: add Batch 60 real-data acceptance coverage
fix: prevent cross-project stale-state writes
fix: redact sports UI automation traffic
```

Expected: each commit is independently reviewable and its tests are recorded.

- [ ] **Step 3: Stop before every push for the Batch 48+ confirmation gate**

Present the repository change-summary template and ask exactly:

```text
当前待推送范围如下。是否还有其他变动需要合并？
如果有，我将暂停推送，完成合并和自检后再重新确认。
```

Expected: no push or PR occurs until the user explicitly says there are no other changes and authorizes that exact push.

---

## Self-review

- Spec coverage: local deployment, all routes/functions, repository-backed sports data, mock minimization, positive/negative cases, external blockers, issue recording, operations release architecture, same-digest promotion, production deferral, production evidence and later fixes are represented.
- Placeholder scan: no `TBD`, `TODO`, “implement later”, generic error-handling or unspecified test steps are used.
- Consistency: Batch 60 branch, SHA, worktree, ports, data levels, A01–A14 and artifact paths are consistent across tasks.
