# Batch 61 Production Readiness and Operations Release MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. If those sub-skills are unavailable, use the repository-confirmed Codex Agent Team workflow and preserve the same task boundaries, tests and review gates.

**Goal:** Close the production-safety and test-credibility gaps found in Batch 60, complete an evidence-backed sports API/UI R2 acceptance with real Test5 data where authorized, and deliver a production-grade operations MVP that deploys one immutable frontend/backend/Alembic release unit to the test environment with health checks, audit and application rollback.

**Architecture:** Run Batch 61 as one release train with three independently reviewable workstreams: acceptance hardening, sports API/UI automation, and operations release control. All execution entry points share server-enforced project/environment/production guards; sports evidence is separated into local R1, Test5 R2 and production read-only R3; a standalone release-control domain library creates one immutable manifest, builds once, deploys exact image digests to test, applies a uniquely headed Alembic migration, records hash-linked events and fails closed. Jenkins is only a controlled builder/executor over the versioned CLI contract. The operations API/UI, production deployment, full approval workflow and database restore remain disabled until Batch 62/production infrastructure is authorized.

**Tech Stack:** React 19, TypeScript, Vite 7, Playwright, Vitest, FastAPI, Pydantic 2, SQLAlchemy 2, Alembic, PostgreSQL 16, Pytest, Docker Compose, PowerShell, Jenkins/Runner adapter, JSON Schema and append-only audit evidence.

---

## 1. Release decision and scope

### 1.1 Recommended delivery shape

Batch 61 should be a **15-working-day release train with three parallel workstreams**, not one undifferentiated feature branch. Use three scoped Agent Team worktrees/PRs from the same merged Batch 60 `main` baseline, integrate them in dependency order, then create a final acceptance PR only if evidence reconciliation changes tracked files:

1. `feature/batch-61-production-safety-and-test-credibility`
2. `feature/batch-61-sports-api-ui-r2-acceptance`
3. `feature/batch-61-test-release-control-plane-mvp`

Each PR must pass its own required checks and merge before the next dependent worktree is created. This keeps the safety fixes, test assets and deployment engine independently reversible.

### 1.2 Batch 61 must deliver

- All four Batch 60 P0 issues closed with dynamic evidence, not only code review.
- No open P1 issue involving false-green tests, production mis-trigger, credential leakage, data isolation or high/critical supply-chain risk.
- API execution quick/asset/single/group/batch entry points use one environment, variable, authorization and result contract.
- Sports API/UI tests distinguish `PASS`, `FAIL`, `BLOCKED` and `NOT RUN`; absence of credentials or fixtures can never become `PASS` or a silent skip.
- Authorized Test5 read-only home/list/detail and authentication-negative journeys use current contracts and persisted real data.
- Any Test5 payment/refund/bonus write journey runs only under a separate written authorization, disposable account, cleanup rule and amount ceiling.
- One immutable release manifest binds frontend digest, backend digest, Alembic target, config schema, SBOM, signatures/checksums and QA evidence.
- Test deployment is repeatable and idempotent, records actual digests, holds an environment lock, performs backup/preflight/migration/health/smoke, and supports application rollback.
- Jenkins/CLI shows a sanitized release composition, test deployment timeline, blockers and rollback evidence; production commands return a stable `PRODUCTION_NOT_CONFIGURED` failure.
- Every normally working PC function has a visually audited `1440×900` screenshot and an evidence index entry.

### 1.3 Explicitly deferred from Batch 61

- Production deployment or production database migration.
- Production payment, refund, bonus, publishing, account-management or destructive sports writes.
- Database downgrade automation or automatic restore after a partially applied migration.
- A full multi-approver production workflow, Secret Manager administration, progressive/canary delivery and production SLA dashboard.
- A dedicated operations control-plane REST API and web console. Batch 61 first proves the underlying immutable contract and executor; productized API/UI is Batch 62.
- Replacement of Jenkins with a new runner platform. Batch 61 defines a stable adapter so the executor can be replaced later.

These become Batch 62/63 work only after the test-release MVP has passed a deployment and rollback exercise.

## 2. Entry gates and external prerequisites

### Task 1: Close Batch 60 before opening Batch 61

**Files:**
- Verify: `test-platform-v2/work-logs/batch-60-qa-report.md`
- Verify: `test-platform-v2/work-logs/batch-60-issue-register.md`
- Verify: `test-platform-v2/work-logs/batch-60-sports-api-ui-automation-validation.md`

- [ ] **Step 1: Complete Batch 60 repository hygiene**

Remove untracked runtime output such as `tests/automation/ui/test-results/`, reconcile the B60-P1-007 status across the sports report and issue register, and confirm no database, backup, credential or raw traffic artifact is in the deliverable.

Run: `git status --short`

Expected: every remaining file is an intentional Batch 60 source, test, document or sanitized evidence file.

- [ ] **Step 2: Re-run Batch 60 mandatory gates**

Run:

```powershell
cd test-platform-v2/backend
.venv/Scripts/python.exe -m ruff check app --select F821
.venv/Scripts/python.exe -m pytest tests -q
cd ../frontend
npm test
npm run typecheck
npm run build
cd ../../tests/automation/ui
npm run test:security
npm run typecheck
git diff --check
```

Expected: backend `941 passed, 0 failed, 3 skipped`; frontend `269 passed`; build/type/security checks pass; any count change is documented and has zero new failures.

- [ ] **Step 3: Follow the Batch 60 push and PR gates**

Show the exact AGENTS.md change summary and ask the mandatory per-push authorization question. After authorization, push only the Batch 60 feature branch, create a Draft PR to `main`, wait for required checks, complete the Agent Team identity/final audit gate, and merge through PR.

- [ ] **Step 4: Create Batch 61 only from merged main**

Run:

```powershell
git fetch origin --prune
git rev-parse origin/main
pwsh scripts/git/start-agent-team-task.ps1 `
  -Executor codex -UserConfirmedExecutor `
  -Kind feature `
  -Task batch-61-production-safety-and-test-credibility `
  -Scope test-platform-v2,tests,docs `
  -FrontendPort 5197 -BackendPort 8027
```

Expected: the Batch 61 worktree metadata reports `agent-team`/`codex`, its base equals the merged Batch 60 commit on `origin/main`, and the worktree is clean.

### Task 2: Freeze Batch 61 requirements, owners and evidence rules

**Files:**
- Create: `test-platform-v2/work-logs/batch-61-acceptance-matrix.md`
- Create: `test-platform-v2/work-logs/batch-61-issue-register.md`
- Create: `test-platform-v2/work-logs/batch-61-real-data-manifest.md`
- Create: `test-platform-v2/work-logs/batch-61-pc-usage-snapshot-index.md`
- Create: `test-platform-v2/work-logs/batch-61-release-readiness.md`
- Modify: `test-platform-v2/docs/改进任务backlog.md`

- [ ] **Step 1: Import unresolved Batch 60 findings**

Copy unresolved items with their original IDs and add a `B61 disposition` column. Do not renumber or erase Batch 60 history. Classify each as `MUST`, `SHOULD`, `EXTERNAL BLOCKED` or `DEFERRED`.

Expected MUST set: B60-P0-001 through B60-P0-004; B60-P1-002, 006, 008, 009, 011, 012, 013, 015, 016, 017, 019, 020 and 023; OPS0 and OPS1. Wide API-only capability UI work and non-blocking P2 visual polish remain Batch 62.

- [ ] **Step 2: Record named ownership and prerequisite dates**

For every MUST item record accountable role, implementer, reviewer, start/end milestone, evidence type and blocker owner. External conditions use a dated `BLOCKED` record instead of an assumed delivery date.

By the end of Day 2, freeze the Test5/VPN/contracts/accounts/data/cleanup package and the authorized old PostgreSQL snapshot. If either package is absent, change the target verdict from `READY FOR TEST RELEASE` to `LOCAL HARDENING COMPLETE / EXTERNAL BLOCKED` immediately; do not wait until the final day or invent replacement data.

- [ ] **Step 3: Define the evidence vocabulary**

Use only:

```text
PASS     = expected result and business/API/data/audit evidence all agree
FAIL     = executed and at least one required assertion failed
BLOCKED  = an external prerequisite is absent; no pass credit
NOT RUN  = executable conditions exist but execution has not occurred
DEFERRED = explicitly excluded from Batch 61 scope and approved as such
```

Expected: empty/loading/error/Mock states are never counted as normal-function PASS screenshots.

## 3. Workstream A — production safety and acceptance hardening

### Task 3: Unify production-operation guards

**Files:**
- Create: `test-platform-v2/backend/app/services/production_operation_guard.py`
- Create: `test-platform-v2/backend/tests/test_production_operation_guard.py`
- Modify: `test-platform-v2/backend/app/api/v1/apitest.py`
- Modify: `test-platform-v2/backend/app/api/v1/test_case.py`
- Modify: `test-platform-v2/backend/app/api/v1/release_bundles.py`
- Modify: `test-platform-v2/backend/app/services/integration_service.py`
- Modify: `test-platform-v2/backend/app/seed.py`
- Create: `test-platform-v2/frontend/src/components/ProductionOperationDialog.tsx`
- Create: `test-platform-v2/frontend/src/components/__tests__/ProductionOperationDialog.test.tsx`
- Modify: `test-platform-v2/frontend/src/pages/apitest/components/ApiDebugPanel.tsx`
- Modify: `test-platform-v2/frontend/src/pages/release-bundles/BundleDetail.tsx`
- Modify: `test-platform-v2/frontend/src/pages/integration/index.tsx`

- [ ] **Step 1: Write failing backend policy tests**

Parameterize API quick execution, API case execution, release regression and bilateral integration sync. Assert that production write/trigger actions require all of: project-owned environment, a dedicated permission, `confirm_prod=true`, a human-readable target and an audit event. Assert zero task/run/sync rows are created on rejection.

Run: `.venv/Scripts/python.exe -m pytest tests/test_production_operation_guard.py -q`

Expected before implementation: failures for each remaining unguarded entry point.

- [ ] **Step 2: Implement one server-side guard**

The service contract is:

```python
@dataclass(frozen=True)
class ProductionOperation:
    action: str
    project_id: int
    environment_id: int | None
    permission: str
    confirmed: bool

def require_allowed_operation(
    db: Session,
    operation: ProductionOperation,
    user_permissions: set[str],
) -> Environment | None:
    """Return the project-owned environment or raise before side effects."""
```

Do not trust a frontend label, route name or request URL to infer safety. Unknown/missing environments fail closed for any action that requires an environment.

- [ ] **Step 3: Replace per-page confirmation variants**

Use one dialog that displays project, environment, base URL, operation, read/write classification and affected resource count. Production confirmation is never preselected and cannot be bypassed by keyboard submit.

- [ ] **Step 4: Verify dynamic rejection and success paths**

Run backend tests, relevant Vitest files and a real-browser test at `1440×900`. Capture one authorized test-environment success and one production rejection showing zero created executions.

Expected: B60-P0-004 closes only after all named entry points have dynamic evidence.

### Task 4: Consolidate the five API execution entry points

**Files:**
- Modify: `test-platform-v2/frontend/src/api/apitest.ts`
- Create: `test-platform-v2/frontend/src/pages/apitest/apiExecutionRequest.ts`
- Create: `test-platform-v2/frontend/src/pages/apitest/components/apiExecutionRequest.test.ts`
- Modify: `test-platform-v2/frontend/src/pages/apitest/components/DebugTab.tsx`
- Modify: `test-platform-v2/frontend/src/pages/apitest/components/ApiDebugPanel.tsx`
- Modify: `test-platform-v2/frontend/src/pages/apitest/components/ApiCaseTab.tsx`
- Modify: `test-platform-v2/frontend/src/pages/apitest/components/TaskTab.tsx`
- Modify: `test-platform-v2/backend/app/schemas/api_asset.py`
- Modify: `test-platform-v2/backend/app/services/api_execution_service.py`
- Modify: `test-platform-v2/backend/app/api/v1/apitest.py`
- Modify: `test-platform-v2/backend/app/api/v1/test_case.py`
- Create: `test-platform-v2/backend/tests/test_api_execution_entrypoint_parity.py`
- Create: `test-platform-v2/backend/tests/test_api_execution_target_policy.py`
- Create: `test-platform-v2/backend/tests/test_api_execution_evidence_redaction.py`

- [ ] **Step 1: Define one request and result contract**

```typescript
export type ApiExecutionRequest = {
  source: 'quick' | 'asset' | 'single' | 'group' | 'batch'
  environment_id: number | null
  dataset_id: number | null
  case_ids: number[]
  request: ApiRequestDefinition | null
  confirm_prod: boolean
}
```

All five entry points must return the same resolved environment ID, resolved URL, assertion summary, error classification, timing and execution/audit identifier.

The request definition must carry query parameters through the backend schema and executor; a field displayed in `ApiDebugPanel` but omitted from the actual HTTP request is a release-blocking failure.

- [ ] **Step 2: Write parity tests before refactoring**

Use the same persisted GET case and harmless local POST fixture through all five sources. Verify query parameters and environment variables resolve identically, numeric assertions retain types, production denial is identical and project-crossing environment IDs return 404/403 before network traffic. An empty assertion collection must return `INVALID_CASE` rather than `all_pass=true`; every release-scope API case requires at least status, business-code and core-field assertions.

- [ ] **Step 3: Route every UI entry through the shared builder**

Remove component-local defaults and any fallback that silently drops the selected environment. GET requests may run against production only under the documented read-only rule; non-GET production requests require the production guard.

Absolute URLs must match the project-owned environment host allowlist. Providing an environment must not bypass SSRF validation. Private Test5 hosts are enabled only by an explicit environment policy; redirects are revalidated hop by hop.

- [ ] **Step 4: Verify network cardinality**

In browser evidence, each user execution creates one effective execute request and one persisted execution. React development behavior must not produce duplicate runs. Persisted request/response headers, bodies, dataset rows and task snapshots use recursive allowlisted redaction; unknown binary/raw bodies fail closed instead of being stored.

Expected: B60-P1-019 closes and all five paths can be compared in one report.

### Task 5: Complete isolation, RBAC, accessibility and repository truth

**Files:**
- Modify: `test-platform-v2/frontend/src/layouts/ProjectScopeBoundary.tsx`
- Create: `test-platform-v2/frontend/e2e/batch61-project-isolation-matrix.spec.ts`
- Create: `test-platform-v2/frontend/e2e/batch61-rbac-matrix.spec.ts`
- Create: `test-platform-v2/frontend/e2e/batch61-accessibility.spec.ts`
- Modify: affected route components listed by failing matrix rows
- Modify: `test-platform-v2/frontend/src/pages/testcase/index.tsx`
- Modify: `test-platform-v2/frontend/src/pages/release-bundles/BundleDetail.tsx`
- Modify: `test-platform-v2/frontend/src/router/index.tsx`
- Modify: `test-platform-v2/frontend/src/stores/auth.ts`
- Create: `test-platform-v2/frontend/e2e/batch61-destructive-and-password-guard.spec.ts`
- Modify: `.gitignore`
- Remove from tracking after inspection: `test-platform-v2/frontend/data/platform.db`
- Remove: `test-platform-v2/docs/theme-mockup-v3.html.bak`
- Modify: `test-platform-v2/docs/现状功能PRD.md`
- Modify: `test-platform-v2/README.md`
- Modify: `test-platform-v2/CLAUDE.md`

- [ ] **Step 1: Write the project A→B route matrix**

Cover requirement, testcase, testplan, report, defect, trace, environment, dataset, integration and UI automation. For each route assert one effective list GET after switching, zero stale A rows, project-correct writes and project-correct empty/error state.

- [ ] **Step 2: Write the admin/tester/viewer capability matrix**

Backend denial is authoritative; UI hides or disables unavailable controls with a reason. Cover create/edit/delete/execute/export/manage actions rather than menu visibility alone.

- [ ] **Step 3: Run axe and keyboard acceptance**

At `1440×900`, `768×1024` and `390×844`, cover login, API execution, UI automation, reports, schedules, notifications and release bundles. Required checks: labels, accessible names, focus visibility/order, dialog focus trap/restore, table access, contrast and no viewport overflow.

- [ ] **Step 4: Remove tracked runtime artifacts safely**

Inspect the tracked database for sensitive data before removal. If sensitive data exists, open an incident record and rotate affected secrets before continuing. Add policy tests or ignore rules preventing `.db`, `.sqlite`, `.bak`, Playwright `test-results/` and raw traffic artifacts from returning.

- [ ] **Step 5: Harden destructive actions and forced password change**

Batch delete shows project, count and irreversible scope; cancel creates zero writes; repeated submit is idempotent; partial server failure is atomic and audited. A `must_change_password` user may access only change-password and logout routes/APIs until success; weak password, cancellation, expired token and direct-route bypass are rejected; old sessions are invalidated after change.

- [ ] **Step 6: Preserve release interaction annotations**

Persisted `page_interactions` must render, edit by keyboard, save and reload with schema equality. Invalid historical values show a controlled migration/error message and are never silently replaced with an empty set.

- [ ] **Step 7: Rebuild the fact-source documentation**

Document the actual React/FastAPI versions, cookie-session behavior, module inventory, mature/partial/blocked capability state, current OpenAPI behavior and the difference between local Runner validation and sports business E2E.

Expected: B60-P0-003 and B60-P1-002/006/008/009/011/015/016/017/020 close with matrix evidence.

## 4. Workstream B — sports API and UI automation R2 acceptance

### Task 6: Make the sports Playwright suite fail truthfully

**Files:**
- Modify: `tests/automation/ui/utils/auth.ts`
- Modify: `tests/automation/ui/utils/traffic-capture.ts`
- Modify: `tests/automation/ui/utils/ai-test.ts`
- Create: `tests/automation/ui/utils/preconditions.ts`
- Create: `tests/automation/ui/utils/test-data.ts`
- Modify: `tests/automation/ui/tests/home/home-recommend.spec.ts`
- Modify: `tests/automation/ui/tests/list/article-list.spec.ts`
- Modify: `tests/automation/ui/tests/detail/article-detail.spec.ts`
- Modify: `tests/automation/ui/tests/pay/recharge.spec.ts`
- Modify: `tests/automation/ui/tests/refund/first-bet-protection.spec.ts`
- Modify: `tests/automation/ui/tests/bonus/bonus-camel-coins.spec.ts`
- Create: `tests/automation/ui/tests/admin/content-and-order-readonly.spec.ts`
- Modify: `tests/automation/ui/playwright.config.ts`
- Modify: `tests/automation/ui/package.json`

- [ ] **Step 1: Replace silent skips with explicit precondition results**

`requireTestData()` must throw a structured `BLOCKED` error containing the missing dataset key and owner. Only browser/feature incompatibility may use Playwright skip, and every skip must have a fixed issue ID.

Remove the default `https://g3-test3.elelive.cn` base URL. The suite starts only when target environment, base URL, run level and authorization allowlist are explicit; otherwise it exits `BLOCKED` before opening a browser or sending network traffic.

- [ ] **Step 2: Add result assertions to every P0 journey**

Each journey needs: visible business result, relevant API response assertion, traffic redaction assertion and persisted screenshot/JSON evidence. “Click succeeded”, “page did not crash” and AI narration are not acceptance assertions. AI vision may assist element location, but payment, refund, ordering, entitlement and balance use deterministic DOM/API/database/audit oracles.

- [ ] **Step 3: Add deterministic real-data selection**

Select stable Test5 records by documented business key, not first row or random content. Read-only journeys may reuse records; write journeys require an allocated disposable identity and cleanup API/owner.

Scan generated traces, screenshots, JSON, HTML and logs using injected canary credentials and representative nested PII. URL/query/header/request body/response header/response body redaction must produce zero canary hits and preserve correlation IDs needed for debugging.

- [ ] **Step 4: Add minimal operations-admin read-only coverage**

Cover content lookup and order lookup needed to verify the user-side article/payment/refund chain. Do not add production admin writes.

Expected: zero unexplained skips, every collected P0 journey has at least one explicit business assertion, and B60-P1-012 closes.

### Task 7: Repair production-smoke semantics and automation supply chain

**Files:**
- Modify: `test-platform-v2/backend/tests/playwright/specs/production-smoke.spec.ts`
- Modify: `test-platform-v2/backend/tests/playwright/specs/production-web-smoke.spec.ts`
- Modify: `tests/automation/ui/package.json`
- Modify: `tests/automation/ui/package-lock.json`
- Modify: `tests/automation/ui/utils/ai-test.ts`
- Modify: `tests/automation/ui/tests/security/security-utils.spec.ts`
- Create: `tests/automation/ui/tests/security/no-false-green.spec.ts`

- [ ] **Step 1: Write false-green regression tests**

Assert missing credentials, login rejection, zero API assets and absent business fixtures produce `BLOCKED` or `FAIL`, never `PASS`. Remove boolean assertions that can succeed for both branches.

- [ ] **Step 2: Upgrade Midscene in an isolated compatibility change**

Upgrade from `@midscene/web@0.20.1` to an audited supported 1.x version. Adapt changed APIs without sending credentials, tokens, personal data or raw responses to the model.

- [ ] **Step 3: Run dependency and behavioral gates**

Run:

```powershell
npm ci
npm audit --omit=dev
npm run typecheck
npm run test:security
npx playwright test --list
```

Expected: zero high/critical production dependency vulnerabilities; security red-team tests pass; the expected sports suite is collected; no credential-bearing prompt or artifact is generated.

- [ ] **Step 4: Run backend dependency audit**

Install/use the repository-approved locked `pip-audit` tool and save the JSON report outside source artifacts before adding a sanitized summary to QA evidence.

Expected: zero unaccepted high/critical findings. Accepted lower-risk findings have owner, expiry, exploitability and upgrade trigger.

### Task 8: Execute the sports API contract matrix

**Files:**
- Create: `tests/test-cases/batch-61-sports-api-cases.md`
- Create: `tests/automation/api/batch61/` test collection following repository conventions
- Create: `test-platform-v2/work-logs/batch-61-sports-api-results.md`
- Store sanitized runtime evidence under: `test-platform-v2/work-logs/evidence/batch-61-sports-platform-validation/api/`

- [ ] **Step 1: Validate prerequisites without changing external state**

Required inputs: authorized OpenVPN window; current `camel`, `live`, `payment`, `studio`, `konfi` and `account` OpenAPI contracts; least-privilege Test5 account/token; rate limit; cleanup and retention rules; current frontend/backend/service SHAs. Stable records include anonymous/normal/low-balance/first-purchase/used-eligibility users, recommended authors and Yield order, categories/pinned/free/paid articles, locked/unlocked and settled Win/Loss predictions, Bonus/non-Bonus packages and readonly operations accounts. Hash and date contracts; never copy credentials into Markdown or Git.

Default authorization is read-only. `live` low-impact create/update may run only with unique Batch 61 names and an approved retention/cleanup rule. `payment` remains read-only unless a separate written authorization explicitly permits a bounded test transaction/refund. DELETE, real charge, transfer, ban, publish, stream and batch mutation remain forbidden by default.

- [ ] **Step 2: Cover each interface with three assertion layers**

For every selected home/list/detail/auth endpoint include:

1. Parameter assertions: required/optional/boundary/type/enum/encoding/repeated/idempotency inputs.
2. Business assertions: identity, entitlement, status transition, pagination/sort/filter semantics and cross-service consistency.
3. Response assertions: status, schema, field types/nullability, error code/message, headers, latency budget and sensitive-data absence.

- [ ] **Step 3: Cover negative and security cases**

Run missing/expired token, wrong role, cross-user/cross-project resource, invalid ID, duplicate request and rate-limit cases. Test5 write cases additionally verify idempotency key, amount ceiling, ledger/order consistency and cleanup.

- [ ] **Step 4: Persist platform execution records**

Import current contracts into the testing platform, execute through the consolidated API engine, and verify UI result, API record, database row and audit export agree. Record the exact environment and contract hash.

Expected: all authorized read-only cases execute; no `BLOCKED` remains for an input already supplied; production receives GET/HEAD only.

### Task 9: Execute the sports UI R2 matrix with real data

**Files:**
- Create: `tests/test-cases/batch-61-sports-ui-cases.md`
- Create: `test-platform-v2/work-logs/batch-61-sports-ui-results.md`
- Store screenshots under: `test-platform-v2/work-logs/evidence/batch-61-sports-platform-validation/pc-usage-snapshots/`
- Store sanitized traces under: `test-platform-v2/work-logs/evidence/batch-61-sports-platform-validation/ui/`

- [ ] **Step 1: Execute read-only critical journeys**

Cover login/session recovery, home recommendations, article list/filter/pagination, article detail/media/error state, user entitlement display, order lookup and admin read-only reconciliation.

- [ ] **Step 2: Execute approved write journeys separately**

Recharge/payment, first-bet protection/refund and Camel Coin bonus tests require explicit Test5 write authorization. Assert UI, API, database/ledger or admin record and audit/event consistency. If authorization is absent, mark each case `BLOCKED` with owner and do not simulate success with Mock data.

- [ ] **Step 3: Validate browser quality**

For each supported journey capture console errors, failed network calls, duplicate requests, keyboard flow, responsive behavior and user-visible recovery. Re-run critical read-only paths in the agreed supported browser matrix.

- [ ] **Step 4: Produce PC evidence**

Capture one `1440×900` image for every normal successful function and additional negative images only when the explicit fail-closed behavior is the expected result. Visually inspect every image for loading spinners, overlap, masked data, stale project context and readable target/environment labels.

Expected: sports status totals are derived from case rows; no screenshot count is used as a substitute for case assertions.

## 5. Workstream C — test-environment operations release MVP

### Task 10: Implement the immutable release-manifest contract

**Files:**
- Create: `deploy/release-control/pyproject.toml`
- Create: `deploy/release-control/requirements.lock`
- Create: `deploy/release-control/src/cameltv_release/__init__.py`
- Create: `deploy/release-control/src/cameltv_release/contracts.py`
- Create: `deploy/release-control/schemas/release-manifest.v1.schema.json`
- Create: `deploy/release-control/schemas/environment.v1.schema.json`
- Create: `deploy/release-control/schemas/deployment-record.v1.schema.json`
- Create: `deploy/release-control/schemas/release-event.v1.schema.json`
- Create: `deploy/release-control/schemas/promotion-attestation.v1.schema.json`
- Create: `deploy/release-control/examples/release-manifest.example.json`
- Create: `deploy/release-control/examples/test-environment.example.json`
- Create: `deploy/release-control/tests/test_contracts.py`

- [ ] **Step 1: Write schema rejection tests**

Reject mutable tags without digests, non-`sha256:` digests, missing SBOM/signature/checksum, multiple or missing Alembic heads, inline secrets, absent QA evidence and an unknown config schema version. Secret references must be versioned and match the target environment.

- [ ] **Step 2: Define the Pydantic source contract**

The checked-in valid fixture uses a concrete non-production release:

```json
{
  "schema_version": "1.0",
  "release_id": "b61-test-20260801-0001",
  "git_sha": "1111111111111111111111111111111111111111",
  "frontend": {
    "image": "registry.test.local/cameltv/platform-frontend",
    "digest": "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "sbom_sha256": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
  },
  "backend": {
    "image": "registry.test.local/cameltv/platform-backend",
    "digest": "sha256:cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc",
    "openapi_sha256": "dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd",
    "sbom_sha256": "eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee"
  },
  "database": {
    "alembic_heads": ["batch61_release_mvp"],
    "target_revision": "batch61_release_mvp",
    "rollback_mode": "application-rollback-or-forward-fix"
  },
  "config_schema": "platform-runtime/v1",
  "secret_refs": ["secret://test/cameltv/platform@v1"],
  "qa_evidence": ["artifact://batch61/qa-report.json"]
}
```

Signed checksum metadata lives beside the manifest and never contains a private key. Deployment IDs, verification time/actor, previous stable release and backup ID are deliberately excluded from the immutable manifest: they belong to `DeploymentRecord` and `PromotionAttestation`, preventing post-deploy evidence from mutating the release.

- [ ] **Step 3: Generate and compare JSON Schema**

`python -m cameltv_release.cli schema-check` must fail if the checked-in schemas differ from their Pydantic models. CI runs the check and validates positive/negative examples. Canonical JSON content produces the manifest SHA; any byte-significant field change requires a new release ID.

Expected: OPS0 manifest contract is machine-verifiable and immutable by content hash.

### Task 11: Build the test deployment state machine and fail-closed preflight

**Files:**
- Create: `deploy/release-control/src/cameltv_release/cli.py`
- Create: `deploy/release-control/src/cameltv_release/state_machine.py`
- Create: `deploy/release-control/src/cameltv_release/store.py`
- Create: `deploy/release-control/src/cameltv_release/executor.py`
- Create: `deploy/release-control/src/cameltv_release/probes.py`
- Create: `deploy/release-control/src/cameltv_release/security.py`
- Create: `deploy/release-control/tests/test_state_machine.py`
- Create: `deploy/release-control/tests/test_idempotency_and_locking.py`
- Create: `deploy/release-control/tests/test_event_store_recovery.py`
- Create: `deploy/release-control/tests/test_redaction.py`
- Create: `deploy/release-control/tests/test_failure_recovery.py`

- [ ] **Step 1: Test the legal state graph**

Allowed test path:

```text
DRAFT → VALIDATED → BUILT → TEST_DEPLOYING → TEST_VERIFYING → TEST_VERIFIED
                              ↘ TEST_FAILED
TEST_VERIFIED/TEST_FAILED → TEST_ROLLING_BACK → TEST_ROLLED_BACK
```

All production transitions return `PRODUCTION_NOT_CONFIGURED` in Batch 61. State changes are compare-and-set and include an idempotency key formed from environment, release, operation and caller key.

- [ ] **Step 2: Implement ordered preflight**

Before side effects validate: manifest checksum/signature policy, image availability by digest, SBOM/vulnerability policy, environment lock, environment identity, Secret references, current/unique Alembic head, disk/capacity baseline, database connectivity and backup destination.

- [ ] **Step 3: Implement the deployment sequence**

For test only:

1. acquire environment lock;
2. record current release and actual digests;
3. create and verify database backup metadata;
4. run one exclusive Alembic migration job;
5. pull and start backend by digest;
6. pass backend health/readiness/OpenAPI checks;
7. pull and start frontend by digest;
8. pass Nginx/static/same-origin proxy checks;
9. execute the required smoke plan;
10. compare actual digests and Alembic revision with the manifest;
11. write append-only audit events and release the lock.

Any failed required step stops the sequence. Never continue to frontend after a failed migration/backend health check. State and hash-linked append-only events live in a persistent executor directory outside the Jenkins workspace so `cleanWs` cannot erase release truth; process restart resumes from recorded phases without repeating migration or backup.

- [ ] **Step 4: Implement application rollback**

Rollback returns frontend/backend to the previous stable digests and verifies health. It does not automatically downgrade schema. If the new schema is incompatible with the prior backend, return `FORWARD_FIX_REQUIRED` and preserve the failed release evidence.

- [ ] **Step 5: Run failure injection tests**

Inject missing Secret, manifest tamper, digest mismatch, two Alembic heads, backup failure, migration failure, backend health failure, frontend health failure, smoke failure, competing environment lock and repeated idempotency key.

Expected: no later step executes after the first failure; audit ends in a truthful terminal state; stable service is preserved or restored where the compatibility contract permits.

### Task 12: Add the Jenkins/Runner adapter and immutable test deployment definition

**Files:**
- Create: `test-platform-v2/deploy/docker-compose.release.yml`
- Create: `test-platform-v2/deploy/environments/test.example.json`
- Create: `deploy/release-control/src/cameltv_release/compose_adapter.py`
- Create: `deploy/release-control/src/cameltv_release/jenkins_adapter.py`
- Create: `deploy/release-control/tests/test_compose_adapter.py`
- Create: `deploy/release-control/tests/test_jenkins_contract.py`
- Modify: `Jenkinsfile`
- Modify: `test-platform-v2/backend/Dockerfile`
- Create: `test-platform-v2/docs/operations/runbooks/test-release.md`
- Create: `test-platform-v2/docs/operations/runbooks/test-application-rollback.md`
- Create: `test-platform-v2/docs/operations/runbooks/test-database-recovery.md`
- Modify: `test-platform-v2/deploy/README.md`
- Modify: `test-platform-v2/deploy/CLAUDE.md`
- Modify: `deploy/jenkins/README.md`

- [ ] **Step 1: Remove source-build semantics from release deployment**

The release Compose file uses `${FRONTEND_IMAGE}@${FRONTEND_DIGEST}` and `${BACKEND_IMAGE}@${BACKEND_DIGEST}`. It contains no `build:` and no `latest` tag. Runtime configuration comes from environment-specific Secret references and a validated non-secret config document.

Remove hidden migration from the backend container start command. Add one explicit, exclusive migration service/job; the backend starts only after that job succeeds. Do not use `docker compose down` as the normal update path because it expands outage and state-loss risk.

- [ ] **Step 2: Limit the adapter input contract**

Split controlled build from controlled deploy. The build stage checks out merged `main`, produces/pushes immutable images, SBOM/signature/vulnerability evidence and registers a manifest. The deploy job receives only `release_id`, `environment=test` and an idempotency key, then calls the release CLI. It cannot accept an arbitrary branch, Docker tag, migration command or production target, cannot silently auto-deploy test by default, and cannot create a plaintext `.env` in the workspace.

- [ ] **Step 3: Add a production-job contract test**

Scan the production adapter definition and fail if it contains checkout, build, install, mutable tag or source-path deployment steps. In Batch 61 the production adapter is a rejecting stub with exit code non-zero and reason `PRODUCTION_NOT_CONFIGURED`.

- [ ] **Step 4: Write the operator runbook**

Include prerequisites, manifest registration, dry run, test deployment, health verification, evidence export, retry semantics, application rollback, forward-fix escalation, lock recovery and secret-redaction checks. Use concrete command forms but no real credentials.

Expected: an operator can perform a test dry run and rollback without editing source or logging into the application host for ad hoc commands.

### Task 13: Persist deployment truth and issue a test promotion attestation

**Files:**
- Modify: `deploy/release-control/src/cameltv_release/store.py`
- Create: `deploy/release-control/src/cameltv_release/attestation.py`
- Create: `deploy/release-control/tests/test_promotion_attestation.py`
- Create: `deploy/release-control/tests/test_event_hash_chain.py`
- Create: `deploy/release-control/README.md`
- Create: `test-platform-v2/work-logs/batch-61-release-evidence-index.md`

- [ ] **Step 1: Persist deployment records without secrets**

Use a durable SQLite state store under an executor-controlled persistent directory, not the application database or Jenkins workspace. Persist release/manifest hash, environment, idempotency/correlation IDs, observed digests, Alembic before/after, previous release, backup reference, probe summary, sanitized error class and timestamps. Store only versioned Secret references.

- [ ] **Step 2: Make audit tamper-evident**

Every append-only release event contains sequence, actor, release/deployment/environment IDs, from/to state, phase, reason, evidence references, previous event hash and event hash. Verification fails on edits, deletion, reordering or broken correlation.

- [ ] **Step 3: Issue a separate promotion attestation**

After `TEST_VERIFIED`, create a signed/checksummed `PromotionAttestation` binding the immutable manifest hash to the actual test deployment, observed frontend/backend digests, observed Alembic revision, verifier and QA evidence. Never write test results back into the release manifest.

- [ ] **Step 4: Export human and machine evidence**

CLI supports sanitized JSON and Markdown summaries for dry run, deployment, failure and rollback. Capture `1440×900` PC screenshots of the Jenkins release/digest page, `TEST_VERIFIED` stage timeline, a controlled failure/recovery and the sports platform version/health page. Do not fabricate a release-console screenshot because Batch 61 has no product UI.

Expected: normal test release operations need no ad hoc SSH/source edits; release truth survives Jenkins cleanup/restart and can be independently verified. The control-plane API/UI remains a Batch 62 consumer of this domain library.

### Task 14: Exercise real PostgreSQL migration and test deployment

**Files:**
- Create: `deploy/release-control/tests/test_postgres_release_migration.py`
- Create: `test-platform-v2/work-logs/batch-61-test-release-exercise.md`
- Store sanitized evidence under: `test-platform-v2/work-logs/evidence/batch-61-release-exercise/`

- [ ] **Step 1: Validate an empty PostgreSQL 16 install**

Assert one Alembic head, upgrade to head, seed idempotency, application health and no runtime `create_all` dependency.

- [ ] **Step 2: Restore the authorized old snapshot**

Record source version/hash and sanitized row-count invariants. Run backup, upgrade and application/API checks. If the snapshot is unavailable, this row remains `BLOCKED`; SQLite cannot satisfy it.

- [ ] **Step 3: Deploy one immutable release to test**

Build once in the controlled builder, record digests/SBOM/checksums, register the manifest, dry-run, deploy test and verify running digests/revision exactly match.

- [ ] **Step 4: Perform a rollback exercise**

Inject a post-deployment health failure or use a dedicated non-production failure fixture, roll applications back to the previous stable digests, verify health and preserve the database compatibility decision.

Expected: A13 becomes `PASS FOR TEST MVP`; production remains `DEFERRED`, not falsely upgraded to PASS.

## 6. Final production-grade acceptance

### Task 15: Run full-platform regression and evidence reconciliation

**Files:**
- Modify: `test-platform-v2/work-logs/batch-61-acceptance-matrix.md`
- Modify: `test-platform-v2/work-logs/batch-61-issue-register.md`
- Modify: `test-platform-v2/work-logs/batch-61-real-data-manifest.md`
- Modify: `test-platform-v2/work-logs/batch-61-pc-usage-snapshot-index.md`
- Create: `test-platform-v2/work-logs/batch-61-qa-report.md`

- [ ] **Step 1: Run mandatory code and dependency gates**

```powershell
cd test-platform-v2/backend
.venv/Scripts/python.exe -m ruff check app --select F821
.venv/Scripts/python.exe -m pytest tests -q
.venv/Scripts/pip-audit.exe --format json --output ../../work-logs/evidence/batch-61-backend-audit.json
cd ../frontend
npm test
npm run typecheck
npm run build
npm audit --omit=dev
cd ../../tests/automation/ui
npm ci
npm run test:security
npm run typecheck
npm audit --omit=dev
cd ../../../deploy/release-control
python -m pytest tests -q
python -m cameltv_release.cli schema-check
git diff --check
```

Expected: zero test failures, zero F821/type/build/schema failures and zero unaccepted high/critical runtime vulnerabilities.

- [ ] **Step 2: Run the full functional matrix**

Revisit every platform module and every normal action: list/search/filter/pagination/detail/create/edit/delete/batch/export/import/execute/state transition/permission/error/retry where applicable. Validate UI/API/database/audit consistency and one effective GET per request-triggering effect.

- [ ] **Step 3: Reconcile all evidence indexes mechanically**

Check that every indexed PNG/CSV/JSON exists, every PASS links to evidence, every screenshot has a unique ID, every issue status agrees across register/matrix/QA report, and raw secrets/tokens/personal data are absent.

- [ ] **Step 4: Issue the Batch 61 verdict**

Allowed verdicts:

- `READY FOR TEST RELEASE`: all Batch 61 MUST gates pass and test release/rollback exercise succeeds.
- `CONDITIONAL`: only explicitly approved external write journeys or old-snapshot migration remain blocked; no P0 or safety/false-green/high-risk P1 remains.
- `NEEDS WORK`: any P0, false-green, isolation, high/critical dependency, digest mismatch, migration/backup, rollback or evidence-integrity gate fails.

Production stays `DEFERRED` until the separately scoped production infrastructure and approval gates are built and exercised.

### Task 16: Complete delivery governance

**Files:**
- Modify as needed: `.github/pull_request_template.md` evidence section only if the current template cannot represent the new release evidence
- Modify: `test-platform-v2/docs/改进任务backlog.md`
- Modify: `docs/adr/0015-operations-release-control-plane.md` status/phase evidence

- [ ] **Step 1: Record exact self-check outputs and failure sets**

The QA report includes commands, exit codes, collected/passed/failed/skipped counts, dependency findings, browser scope, external blockers and CI range classification.

- [ ] **Step 2: Show the required per-push summary**

Use the exact AGENTS.md template and ask verbatim:

```text
当前待推送范围如下。是否还有其他变动需要合并？
如果有，我将暂停推送，完成合并和自检后再重新确认。
```

Do not push, create a PR or reuse authorization after the file set changes without asking again.

- [ ] **Step 3: Complete Draft PR, checks, Agent Team final confirmation and merge**

Never push `main`. Merge only through the protected PR workflow after all required checks and the final executor/authorization audit pass.

## 7. Milestones, staffing and go/no-go gates

| Milestone | Working days | Primary output | Exit gate |
| --- | ---: | --- | --- |
| M0 Batch 60 closure | Before Day 1 | Batch 60 merged to `main` | CI green; clean new baseline |
| M1 Safety hardening | Days 1–5 | Unified production guard, API parity, isolation/RBAC baseline | 4 P0 dynamically closed; no side effect on rejected action |
| M2 Sports test credibility | Days 4–11 | Truthful Playwright/API suite, dependency upgrades, Test5 read-only evidence | No false green; zero high/critical; authorized R2 reads executed |
| M3 Release contract/engine | Days 3–11 | Manifest schema, state machine, CLI, Jenkins adapter, rollback | Failure-injection suite green; source-free digest deployment |
| M4 Real exercises | Days 12–13 | Test5 R2, PostgreSQL/test deploy and rollback evidence | Actual digests/revision match manifest; audit complete |
| M5 Full acceptance | Days 14–15 | Full matrix, PC evidence, QA report and release verdict | All MUST gates resolved; PR checks green |

Recommended minimum team capacity: one backend/architecture owner, one frontend owner, one sports automation QA, one DevOps owner, and one independent acceptance reviewer. Agent Team can parallelize implementation and test review, but the DevOps/environment owner must remain a human accountable role for external credentials, Test5 writes and deployment authorization. If these three implementation streams cannot run concurrently, re-baseline to 20 working days rather than dropping safety evidence.

## 8. Batch 61 release gates

Batch 61 is complete only when all applicable gates below are evidenced:

- **Safety:** 0 open P0; no unguarded production action; no secret/PII in prompts, logs, traces or screenshots.
- **Correctness:** full backend/frontend suites pass; five API entry points are behaviorally equivalent; no unexplained Playwright skips.
- **Sports R2:** all authorized read-only API/UI critical journeys executed with current contracts and real stable data; write journeys are either separately authorized and reconciled or explicitly BLOCKED.
- **Sports case thresholds:** starting baseline is API `5/16 PASS` and UI `9/23 PASS`. Release-scope P0/P1 execution and pass rates must both be 100%, with zero FAIL/BLOCKED/NOT RUN/runtime skip; if an external prerequisite prevents that threshold, the verdict cannot be `READY`. P2 exceptions need written owner, expiry and retest trigger.
- **Sports deterministic evidence:** every API case has HTTP/business/core-data assertions; every write has read-back, database/audit reconciliation and cleanup; every UI P0/P1 has a DOM/API/data oracle and passes three consecutive first runs without retry-dependent green.
- **Supply chain:** zero unaccepted high/critical runtime vulnerabilities; SBOM and immutable digests are bound to the release.
- **Database:** unique Alembic head; backup/preflight/upgrade evidence; old snapshot tested when supplied; runtime `create_all` disabled in release environments.
- **Operations:** test deployment and application rollback exercise pass; actual frontend/backend digests and database revision equal the manifest; retries are idempotent; failure is fail-closed.
- **UX/a11y:** target product routes pass desktop/tablet/mobile keyboard and axe checks; no blocking overflow; every normal successful PC function has a reviewed `1440×900` snapshot; release execution has equivalent Jenkins/real-platform PC evidence until the Batch 62 operations UI exists.
- **Governance:** issue/matrix/evidence/report totals agree; Batch 61 merged by PR only; production remains disabled until its own infrastructure and approval phase is accepted.

## 9. Decisions the product owner should make before Day 1

1. Approve the Batch 61 boundary: test-release MVP now; full production control plane and production cutover in Batch 62/63.
2. Name the Test5/VPN, sports data, DevOps and release-verdict owners.
3. Provide or explicitly decline the six current Test5 contracts, least-privilege credentials, stable record keys and cleanup rules.
4. Separately authorize or forbid Test5 payment/refund/bonus write tests, including account, ceiling, window and rollback/cleanup owner.
5. Confirm the test registry, Jenkins/Runner, PostgreSQL, backup location and Secret-reference mechanism for the release exercise.
6. Approve the 15-day, three-stream baseline. If the named owners cannot work concurrently, approve 20 working days; do not reintroduce the operations UI or reduce safety/testing evidence to preserve the date.
