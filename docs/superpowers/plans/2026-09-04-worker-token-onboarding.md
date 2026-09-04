# Worker Token Onboarding Implementation Plan

> **For agentic workers:** Execute inline in the current Codex Agent Team worktree. Subagents are not authorized for this batch. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let a black-box administrator generate, configure, rotate, and revoke a least-privilege Worker Token through the test-platform frontend, and make that token authenticate real Worker heartbeats.

**Architecture:** Reuse the existing project-scoped `ApiToken` hash and lifecycle. The machine-only heartbeat endpoint validates a `workers:register` scope, while human Worker list/manage endpoints retain session RBAC. Runtime deep-links into a purpose-driven Token form; the one-time success state derives a copyable Worker configuration without persisting the secret.

**Tech Stack:** FastAPI, SQLAlchemy, React 19, TypeScript, React Hook Form, Zod, shadcn/ui, Vitest, Pytest, Playwright CLI.

---

### Task 1: Authenticate Heartbeats With a Worker-Scoped API Token

**Files:**
- Create: `test-platform-v2/backend/tests/aitde/v34/test_worker_token_auth.py`
- Modify: `test-platform-v2/backend/app/services/token_service.py`
- Modify: `test-platform-v2/backend/app/api/v2/workflows.py`

- [ ] Write an integration test that creates a `workers:register` API Token, clears login cookies, posts a valid heartbeat without `X-Project-Id`, and asserts HTTP 200 plus `ONLINE`.
- [ ] Run the new test and verify it fails with HTTP 401 under the current JWT-only dependency.
- [ ] Add a reusable token-scope check in `token_service.py` and a heartbeat dependency that hashes the bearer token through the existing verifier.
- [ ] Update `last_used_at` in the same transaction as successful registration.
- [ ] Add tests that a `trigger` Token gets HTTP 403 and a disabled Worker Token gets HTTP 401.
- [ ] Run the focused backend tests and commit Slice 1.

### Task 2: Make the Worker Token Flow Discoverable

**Files:**
- Modify: `test-platform-v2/frontend/src/pages/runtime/index.tsx`
- Modify: `test-platform-v2/frontend/src/pages/runtime/__tests__/RuntimeAdminPage.test.tsx`
- Modify: `test-platform-v2/frontend/src/pages/system/index.tsx`
- Create: `test-platform-v2/frontend/src/pages/system/tokenPurposes.ts`
- Create: `test-platform-v2/frontend/src/pages/system/tokenPurposes.test.ts`

- [ ] Extend the Runtime page test to expect an administrator link to `/system?tab=tokens&purpose=worker` and a non-manager guidance state.
- [ ] Run the test and verify the missing link fails.
- [ ] Add a semantic Worker onboarding band that checks `token:manage` and renders either the link or contact-admin guidance.
- [ ] Add URL-controlled System tabs so `tab=tokens` reliably opens API Token management.
- [ ] Add pure purpose-to-scope mapping for CI (`trigger`) and Worker (`workers:register`), with tests.
- [ ] Run focused frontend tests and commit Slice 2.

### Task 3: Render One-Time Worker Configuration

**Files:**
- Modify: `test-platform-v2/frontend/src/pages/system/TokensTab.tsx`
- Create: `test-platform-v2/frontend/src/pages/system/__tests__/TokensTab.test.tsx`
- Modify: `test-platform-v2/frontend/src/pages/system/tokenScopes.ts`
- Modify: `test-platform-v2/frontend/src/pages/system/tokenScopes.test.ts`

- [ ] Write a component test that opens a Worker-purpose form, creates with `workers:register`, and sees the fake secret plus copyable backend configuration exactly in the success dialog.
- [ ] Verify the test fails before implementation.
- [ ] Add a labeled purpose Select and submit the mapped minimal scope.
- [ ] Show the Worker configuration only for Worker-purpose results; implement copy success/failure feedback and clear result state on close.
- [ ] Map known scopes to readable Chinese labels and explain existing disable/delete revocation in the UI.
- [ ] Add loading/error handling that prevents duplicate token creation and preserves the form on failure.
- [ ] Run focused frontend tests and commit Slice 3.

### Task 4: Fail Fast and Document the Executable Runbook

**Files:**
- Modify: `test-platform-v2/backend/tests/aitde/v34/test_worker_heartbeat.py`
- Modify: `test-platform-v2/deploy/aitde-runtime/scripts/start-worker.sh`
- Modify: `test-platform-v2/deploy/aitde-runtime/README.md`

- [ ] Add a launcher contract assertion that an empty `API_TOKEN` exits before either Python child process starts.
- [ ] Run it and verify the current script fails the assertion.
- [ ] Add the empty-token guard with an actionable frontend path and no secret echo.
- [ ] Document UI generation, secret injection, success verification, rotation, and revocation order.
- [ ] Run heartbeat/launcher tests and commit Slice 4.

### Task 5: Verify and Deliver

**Files:**
- Create: `work-logs/evidence/batch-229-worker-token-onboarding/README.md`
- Create: `work-logs/batch-229-worker-token-onboarding-qa-report.md`
- Create: `work-logs/batch-229-worker-token-onboarding-leader-verdict.md`
- Modify: `work-logs/kanbans/DEV-batch-229-worker-token-onboarding.md`

- [ ] Run related Pytest/Vitest, backend import/F821/Alembic guards, frontend typecheck/lint/build, `scan-common-bugs.ps1`, and `dev-gate.ps1`.
- [ ] Run backend and frontend full regression; record exact exit codes and failure sets.
- [ ] Start the isolated local backend/frontend on ports 8029/5199.
- [ ] Use Playwright CLI through the rendered frontend to verify Runtime discovery, deep-linking, purpose selection, one-time result, revocation controls, console, and request counts at 1440x900, 768x1024, and 390x844. Never screenshot the secret dialog.
- [ ] Scan changed files and evidence for credential patterns; write QA report and provisional Leader verdict.
- [ ] Review plan coverage, placeholder scan, and type consistency; resolve any gap.
- [ ] Show final change scope and ask the exact one-time confirmation before any push or PR creation.
- [ ] After confirmation, push, create Draft PR, audit, wait for required checks, fix only with renewed confirmation if scope changes, then final-audit and squash merge to `main`.
