# Batch 55 Acceptance Closure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax (`- [ ]`) for tracking.

**Goal:** Replace the unsafe and non-executable Batch 55 acceptance work with a small, truthful, production-grade closure that fixes the `/apitest` proxy regression, makes local seeded credentials repeatable, documents and exercises migration recovery, and records unresolved full-platform coverage for Batch 56.

**Architecture:** Reimplement from `origin/main` in the verified Codex Agent Team worktree. Do not cherry-pick the old Batch 55 branch because its history contains a tracked executor metadata file and plaintext credentials. Keep deterministic unit/Pytest checks in CI, use Playwright against real Vite and FastAPI processes for browser evidence, and keep delivery status separate from the later Batch 56 all-function acceptance.

**Tech Stack:** React 18, TypeScript, Vite 7, Vitest 4, Playwright 1.61, FastAPI, SQLAlchemy 2, Pytest, Alembic, PowerShell, GitHub Actions.

---

## Scope and acceptance rules

- [ ] Work only in `F:\CamelTv-worktrees\codex-batch-55-acceptance-closure` on `fix/batch-55-acceptance-closure`.
- [ ] Preserve the dirty control worktree at `F:\CamelTv`; do not move, delete, stage, or rewrite its files.
- [ ] Do not copy `backend/qa_slice*.py`, tracked `.ai-worktree.json`, plaintext credentials, or contradictory Batch 55 reports from the abandoned branch.
- [ ] Treat `PASS`, `FAIL`, `BLOCKED`, and `NOT RUN` as distinct states. A blocked or unexecuted check never contributes to a pass count.
- [ ] Close C55-1 and C55-2 only after their automated evidence passes. Keep C55-3 through C55-5 open until Batch 56 supplies the required Pytest and real-browser evidence.
- [ ] Do not start a Batch 56 branch until this branch is merged to `main`, remote checks are green, and a fresh fetch confirms the merge.

## Task 1: Lock the clean-room delivery boundary

**Files:**

- Create: `test-platform-v2/work-logs/batch-55-acceptance-closure-issue-register.md`
- Create: `test-platform-v2/work-logs/evidence/batch-55-acceptance-closure/README.md`

- [ ] Record the current `origin/main` SHA, worktree path, branch, workflow `agent-team`, executor `codex`, and the abandoned branch name.
- [ ] Record these confirmed defects without copying secrets:
  - tracked local executor metadata;
  - plaintext credential reuse and partial token logging;
  - six scripts outside Pytest collection;
  - HTTP status-only assertions, including accepted `422` and synthetic no-data passes;
  - API-only scripts labelled browser E2E;
  - source-text theme checks labelled visual acceptance;
  - QA `NEEDS WORK` conflicting with closed C conditions.
- [ ] Define the disposal decision: the abandoned branch is never merged or cherry-picked; only independently reproduced code changes may enter this branch.
- [ ] Add an evidence index schema containing case ID, commit SHA, command, exit code, timestamp, environment, evidence file, and redaction result.
- [ ] Run the worktree verifier and save only its non-sensitive result:

```powershell
pwsh scripts/git/verify-ai-worktree.ps1 `
  -RequireClean `
  -RequireMetadata `
  -ExpectedWorkflow agent-team `
  -ExpectedExecutor codex
```

- [ ] Self-review the two documents for passwords, tokens, cookies, database files, and unsupported pass claims.
- [ ] Commit the boundary documents:

```powershell
git add test-platform-v2/work-logs/batch-55-acceptance-closure-issue-register.md `
        test-platform-v2/work-logs/evidence/batch-55-acceptance-closure/README.md `
        docs/superpowers/plans/2026-07-29-batch-55-acceptance-closure.md
git commit -m "docs: establish batch 55 clean-room closure"
```

## Task 2: Make seeded local credentials stable across restarts

**Files:**

- Create: `test-platform-v2/backend/tests/test_seed_credentials.py`
- Modify: `test-platform-v2/backend/app/seed.py`
- Modify: `test-platform-v2/backend/app/core/config.py`
- Modify: `test-platform-v2/backend/.env.example`
- Modify: `test-platform-v2/backend/README.md`

- [ ] Write a failing Pytest that uses a temporary SQLite database and a temporary `SessionLocal`, runs `run_seed()` twice, and asserts:
  - the first run creates admin and tester users;
  - configured credentials authenticate against the stored hashes;
  - the second run does not call `hash_password` for existing seed users;
  - the second run does not print or log a newly generated credential;
  - existing password hashes are unchanged.
- [ ] Write a failing configuration test that asserts production still rejects empty credentials and development documentation does not promise a generated password is valid beyond initial user creation.
- [ ] Refactor `run_seed()` so password generation and hashing occur only inside the missing-user creation path. Do not eagerly evaluate password defaults before `_get_or_create()` knows whether the user exists.
- [ ] Return or retain the generated development credential only long enough to print it once when the user is first created. Never print a token, cookie, password hash, or credential on later restarts.
- [ ] Update comments and docstrings in `config.py` so they describe “initial creation” rather than “valid this session only”.
- [ ] Document the repeatable local-acceptance path: set strong `ADMIN_PASSWORD`, `TESTER_PASSWORD`, and `SECRET_KEY` in ignored `backend/.env` before creating the local database. Do not add real values to tracked files.
- [ ] Run the focused test and security regression:

```powershell
Set-Location test-platform-v2/backend
python -m pytest tests/test_seed_credentials.py tests/test_p1_security_regression.py -q
ruff check app/core/config.py app/seed.py tests/test_seed_credentials.py
```

- [ ] Commit the seed fix:

```powershell
git add test-platform-v2/backend/app/core/config.py `
        test-platform-v2/backend/app/seed.py `
        test-platform-v2/backend/tests/test_seed_credentials.py `
        test-platform-v2/backend/.env.example `
        test-platform-v2/backend/README.md
git commit -m "fix: keep local seed credentials stable"
```

## Task 3: Fix the Vite proxy and API base contract

**Files:**

- Create: `test-platform-v2/frontend/src/config/devProxy.ts`
- Create: `test-platform-v2/frontend/src/config/devProxy.test.ts`
- Create: `test-platform-v2/frontend/src/api/baseUrl.ts`
- Create: `test-platform-v2/frontend/src/api/baseUrl.test.ts`
- Modify: `test-platform-v2/frontend/vite.config.ts`
- Modify: `test-platform-v2/frontend/src/api/client.ts`
- Modify: `test-platform-v2/frontend/src/api/system.ts`
- Modify: `test-platform-v2/frontend/.env.example`
- Modify: `test-platform-v2/frontend/README.md`

- [ ] Write failing table-driven tests for the proxy matcher:

```text
/api/v1                  -> proxy
/api/v1/open/health      -> proxy
/api/v10                 -> frontend
/api                     -> frontend
/apitest                 -> frontend
/api-keys                -> frontend
```

- [ ] Write failing API-base tests for unset, blank, relative, absolute, and trailing-slash values. The default must be `/api/v1`; the direct-backend example must resolve to `http://localhost:8000/api/v1`.
- [ ] Export a pure `API_V1_PROXY_PATTERN` contract from `src/config/devProxy.ts` and use it as the computed proxy key in `vite.config.ts`.
- [ ] Change the Vite default proxy target from `http://127.0.0.1:8002` to the documented `http://127.0.0.1:8000`. Keep independent worktree overrides through ignored `.env.local`.
- [ ] Centralize the API base URL in `src/api/baseUrl.ts`, use it for the Axios client and audit CSV download, and remove the path that begins with the literal string `undefined/system/`.
- [ ] Update `.env.example` and the frontend README so proxy mode and direct mode include the same `/api/v1` contract.
- [ ] Run focused and full frontend unit gates:

```powershell
Set-Location test-platform-v2/frontend
npx vitest run src/config/devProxy.test.ts src/api/baseUrl.test.ts
npm run typecheck
npm test
npm run build
```

- [ ] Commit the proxy and API-base fix:

```powershell
git add test-platform-v2/frontend/vite.config.ts `
        test-platform-v2/frontend/src/config/devProxy.ts `
        test-platform-v2/frontend/src/config/devProxy.test.ts `
        test-platform-v2/frontend/src/api/baseUrl.ts `
        test-platform-v2/frontend/src/api/baseUrl.test.ts `
        test-platform-v2/frontend/src/api/client.ts `
        test-platform-v2/frontend/src/api/system.ts `
        test-platform-v2/frontend/.env.example `
        test-platform-v2/frontend/README.md
git commit -m "fix: isolate api proxy from frontend routes"
```

## Task 4: Add real-browser proxy and login-shell acceptance

**Files:**

- Create: `test-platform-v2/frontend/e2e/batch55-proxy-login.spec.ts`
- Modify: `test-platform-v2/frontend/src/pages/login/index.tsx`
- Modify: `test-platform-v2/frontend/src/pages/login/__tests__/LoginSecurity.test.tsx`

- [ ] Extend the login unit test first to require an empty credential form, an explicit platform heading, and layout classes that use full available width with a maximum width rather than a fixed `380px`.
- [ ] Replace `h-screen`, the fixed card width, blanket gradient, and `shadow-2xl` with token-based `min-h-[100dvh]`, responsive padding, `w-full max-w-[380px]`, and a restrained theme-compatible surface.
- [ ] Add a Playwright test that:
  - opens `/apitest` through the real Vite server and confirms React redirects the protected route to `/login`;
  - checks the login heading and inputs, not merely HTTP status or body length;
  - calls `/api/v1/open/health` through Vite and asserts the backend response contract;
  - captures `console.error`, `pageerror`, and `requestfailed`, requiring all three collections to remain empty;
  - checks no horizontal overflow at `1440x900`, `768x1024`, `390x844`, and `320x568`;
  - runs Axe against the login page and fails on serious or critical violations;
  - writes redacted screenshots under the ignored Playwright result directory.
- [ ] Start FastAPI on this worktree's backend port `8023` with ignored local credentials and its isolated SQLite database.
- [ ] Start Vite on this worktree's frontend port `5193` using the generated `.env.local`.
- [ ] Run the real-browser acceptance:

```powershell
Set-Location test-platform-v2/frontend
$env:BASE_URL = 'http://localhost:5193'
npx playwright test e2e/batch55-proxy-login.spec.ts --project=chromium
```

- [ ] Stop both processes cleanly and confirm no repository database, report directory, screenshot, trace, or credential file is staged.
- [ ] Commit the browser regression and login-shell fix:

```powershell
git add test-platform-v2/frontend/e2e/batch55-proxy-login.spec.ts `
        test-platform-v2/frontend/src/pages/login/index.tsx `
        test-platform-v2/frontend/src/pages/login/__tests__/LoginSecurity.test.tsx
git commit -m "test: verify proxy and login shell in a real browser"
```

## Task 5: Document and rehearse migration recovery

**Files:**

- Create: `test-platform-v2/backend/alembic/README.md`
- Create: `test-platform-v2/backend/tests/test_alembic_runbook.py`
- Modify: `test-platform-v2/backend/app/models/test_case.py`
- Modify: `test-platform-v2/backend/app/schemas/test_case.py`
- Modify: `test-platform-v2/backend/tests/test_testplan.py`

- [ ] Write a failing documentation-contract test that requires the runbook to include:
  - backup and restore;
  - `alembic heads` and the single-head expectation;
  - `alembic current`;
  - `alembic upgrade head`;
  - explicit revision downgrade instead of relative `-1` across merge points;
  - post-migration row-count and application smoke checks;
  - staging rehearsal before any production action;
  - a statement that an empty temporary database is not A10 old-database evidence.
- [ ] Write the migration runbook without fixed revision counts or head names that immediately become stale.
- [ ] Run `alembic check` before declaring the runbook complete. If it finds drift, add a failing behavior/metadata test and repair the model-to-migration contract instead of documenting the drift as acceptable.
- [ ] Use a disposable database only for the Batch 55 migration contract. Run:

```powershell
Set-Location test-platform-v2/backend
python -m alembic heads
python -m alembic current
python -m alembic upgrade head
python -m alembic check
python -m pytest tests/test_alembic_runbook.py tests/test_batch48_requirement_migration.py -q
```

- [ ] If the clean migration chain cannot run on the disposable database, record `FAIL` with the exact command and exit code; do not edit the report to `PASS`.
- [ ] Record the absence of a provided redacted legacy PostgreSQL snapshot as `BLOCKED` for A10. This does not block the scoped Batch 55 proxy/seed fix, but it blocks a full production acceptance verdict.
- [ ] Commit the migration runbook:

```powershell
git add test-platform-v2/backend/alembic/README.md `
        test-platform-v2/backend/tests/test_alembic_runbook.py
git commit -m "docs: add verifiable migration recovery runbook"
```

## Task 6: Produce truthful Batch 55 closure evidence

**Files:**

- Modify: `C-CONDITIONS.md`
- Create: `tests/test-cases/functional/BATCH55-测试平台验收收尾.md`
- Create: `test-platform-v2/work-logs/batch-55-acceptance-closure-qa-report.md`
- Create: `test-platform-v2/work-logs/batch-55-acceptance-closure-leader-verdict.md`
- Modify: `test-platform-v2/work-logs/batch-55-acceptance-closure-issue-register.md`
- Modify: `test-platform-v2/work-logs/evidence/batch-55-acceptance-closure/README.md`

- [ ] Map C55-1 through C55-5 to the production acceptance rules A01 through A12.
- [ ] Mark only the following as eligible for Batch 55 closure:
  - C55-1: Vite `/api/v1` proxy no longer intercepts `/apitest`, with Vitest and Playwright evidence.
  - C55-2: migration runbook and disposable-database rehearsal, with the legacy-database portion explicitly blocked.
- [ ] Keep these conditions open for Batch 56:
  - C55-3: Knowledge, Wiki, and Trace positive, negative, transactional, and project-isolation coverage.
  - C55-4: real-browser user journeys across testcase, plan, execution, report, schedule, and defect lifecycle.
  - C55-5: six-theme, light/dark, all-route, three-viewport, keyboard, Axe, overflow, console, and network coverage.
- [ ] Document the ClearType finding as non-defect evidence: computed styles have no text shadow/filter, a CSS-free control page reproduces the fringe, and `--disable-lcd-text` removes it. Do not claim a CSS fix.
- [ ] Record external production/test/user-requirement/admin-requirement acceptance as `NOT RUN` in Batch 55 and scheduled for Batch 56. Mention environment-variable slots only; never copy credentials.
- [ ] Recalculate C-condition totals mechanically after moving or adding rows.
- [ ] Run a consistency scan that rejects contradictory combinations such as `NEEDS WORK` with “all closed”, and rejects the abandoned `qa_slice` filenames as evidence.
- [ ] Commit the truthful closure records:

```powershell
git add C-CONDITIONS.md `
        tests/test-cases/functional/BATCH55-测试平台验收收尾.md `
        test-platform-v2/work-logs/batch-55-acceptance-closure-qa-report.md `
        test-platform-v2/work-logs/batch-55-acceptance-closure-leader-verdict.md `
        test-platform-v2/work-logs/batch-55-acceptance-closure-issue-register.md `
        test-platform-v2/work-logs/evidence/batch-55-acceptance-closure/README.md
git commit -m "docs: report truthful batch 55 acceptance status"
```

## Task 7: Run full local delivery gates

- [ ] Verify scope and metadata:

```powershell
pwsh scripts/git/verify-ai-worktree.ps1 `
  -RequireClean `
  -RequireMetadata `
  -ExpectedWorkflow agent-team `
  -ExpectedExecutor codex
```

- [ ] Run backend gates:

```powershell
Set-Location test-platform-v2/backend
ruff check app/ --select F821
ruff check app/core/config.py app/seed.py tests/test_seed_credentials.py tests/test_alembic_runbook.py
python -m pytest tests/test_seed_credentials.py tests/test_alembic_runbook.py tests/test_batch48_requirement_migration.py -q
python -m pytest -q
```

- [ ] Run frontend gates:

```powershell
Set-Location test-platform-v2/frontend
npm run typecheck
npm test
npm run build
$env:BASE_URL = 'http://localhost:5193'
npx playwright test e2e/batch55-proxy-login.spec.ts --project=chromium
```

- [ ] Scan tracked changes for debugging statements, plaintext secrets, token fragments, `.ai-worktree.json`, databases, caches, generated reports, and unrelated files.
- [ ] Compare the full test failure set with `origin/main`. Any new failure is blocking. Record historical failures by exact test name and command, never as “historical issue” alone.
- [ ] Update the QA report and evidence index with the final commit SHA, commands, exit codes, environment ports, and redacted evidence paths.
- [ ] Commit only evidence/status corrections produced by these gates:

```powershell
git add test-platform-v2/work-logs/batch-55-acceptance-closure-qa-report.md `
        test-platform-v2/work-logs/batch-55-acceptance-closure-leader-verdict.md `
        test-platform-v2/work-logs/batch-55-acceptance-closure-issue-register.md `
        test-platform-v2/work-logs/evidence/batch-55-acceptance-closure/README.md
git commit -m "test: record batch 55 closure gates"
```

## Task 8: Pause at the mandatory push gate

- [ ] Show the user the exact branch, target, changed files, commit range, test commands, exit codes, failure set, and risk rating.
- [ ] Ask exactly:

```text
当前待推送范围如下。是否还有其他变动需要合并？
如果有，我将暂停推送，完成合并和自检后再重新确认。
```

- [ ] Do not push, create a PR, or start Batch 56 until the user explicitly states that there are no other changes and authorizes this exact push.
- [ ] After authorization, push only `fix/batch-55-acceptance-closure`, create a Draft PR to `main`, run the Agent Team PR audit, and wait for first-round checks.
- [ ] Ask the required second executor/final-audit authorization after first-round checks. Record completion only if the user reconfirms Codex.
- [ ] Any evidence commit after that point requires a fresh per-push scope summary and the same two-line question.
- [ ] Merge only through the protected PR flow when required checks and the final audit are successful.

## Task 9: Hand off to Batch 56 only after merge

- [ ] Fetch `origin` and verify `origin/main` contains the merged Batch 55 closure.
- [ ] Use `scripts/git/start-agent-team-task.ps1` with executor `codex`, branch `feature/batch-56-full-platform-production-acceptance`, frontend port `5173`, backend port `8000`, and a new isolated worktree.
- [ ] Create a separate Batch 56 implementation plan covering:
  - production acceptance inputs derived from the customer-facing PRDs, Blue Lake requirement evidence, baseline/admin functional cases, traceability matrices, OpenAPI specification, and environment/account index referenced by `docs/测试平台全功能验收文档-环境链接与账号汇总.md`;
  - an input manifest classifying evidence as R0 (authorized live customer input), R1 (redacted source-preserving snapshot with provenance and SHA-256), R2 (schema-faithful generated boundary/load data), or M (mock); every P0/P1 primary journey requires R0 or R1, while R2/M results are reported separately and never close a production gate;
  - realistic document imports, API definitions, requirement text, test cases, plans, schedules, defects, search terms, pagination volumes, and role/project boundaries that preserve the structure and constraints of those customer inputs;
  - real React → FastAPI → database journeys for every release verdict; mocks may cover otherwise unreachable third-party failure branches, but mock-only, status-only, or synthetic no-data results never count as production acceptance evidence;
  - an isolated PostgreSQL acceptance database for production-grade journeys; SQLite remains a fast regression layer and cannot substitute for PostgreSQL concurrency or migration evidence;
  - A01–A12 across all static and dynamic routes;
  - real backend, admin/tester RBAC, cross-project isolation, transactions, rollback, idempotency, concurrency, pagination, search, and count consistency;
  - six themes and supported light/dark modes at `1440x900`, `768x1024`, and `390x844`;
  - keyboard, focus, Axe, overflow, console, failed requests, and one-effective-GET checks;
  - local user acceptance at `http://localhost:5173`;
  - read-only production sports-site comparison;
  - controlled write journeys only in explicitly authorized test environments;
  - unique acceptance-data prefixes, state readback, audit/database verification, and proven cleanup for every controlled write journey;
  - `BATCH56_ACCEPTANCE_REQUIRED=1` semantics: missing real inputs, PostgreSQL, or required credentials produces `FAIL`/`BLOCKED`, never a passing skip;
  - user-side and operations-side requirement comparison;
  - truthful `BLOCKED` status for missing VPN, credentials, Blue Lake URLs, AI key, ELK access, production admin access, or legacy database snapshot.
