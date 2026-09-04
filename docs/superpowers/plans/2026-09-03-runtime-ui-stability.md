# Runtime UI Stability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stop mission tab request loops, keep live Runtime Workers online through continuous heartbeats, and make onboarding/Runtime status accurate and actionable.

**Architecture:** Mission pages use an explicit reload version separate from render state and propagate AbortSignal into Axios. Worker list responses are assembled with one bulk capability query. A small Python heartbeat process runs beside the Temporal Worker under the existing shell launcher, retries transient Control Plane errors, and shares its shutdown lifecycle; the UI reports offline state without pretending it can start remote infrastructure.

**Tech Stack:** React 19, TypeScript, Vitest, Testing Library, Axios, FastAPI, SQLAlchemy 2, httpx, pytest, Bash, shadcn/ui, Tailwind CSS.

---

### Task 1: Mission Scope Request Stability

**Files:**
- Create: `test-platform-v2/frontend/src/pages/missions/__tests__/ScopePage.test.tsx`
- Modify: `test-platform-v2/frontend/src/pages/missions/scope.tsx`
- Modify: `test-platform-v2/frontend/src/api/scope.ts`

- [ ] **Step 1: Write the failing mount/request test**

Render `/missions/3/scope`, resolve `fetchMissionScope` with one item, wait for that item, and assert the mock was called exactly once with mission id `3` and an `AbortSignal`.

- [ ] **Step 2: Run the test and verify the failure**

Run: `npm test -- --run src/pages/missions/__tests__/ScopePage.test.tsx`

Expected: FAIL because the current loading dependency reissues the request and the API receives no signal.

- [ ] **Step 3: Implement an explicit reload version**

Replace the `loading` dependency with `reloadVersion`, increment it from `reload()`, and call `fetchMissionScope(missionId, signal)`. Extend the API signature to pass `{ signal }` to Axios.

- [ ] **Step 4: Verify the focused test**

Run: `npm test -- --run src/pages/missions/__tests__/ScopePage.test.tsx`

Expected: PASS with one request on mount.

### Task 2: Mission Scenario Request Stability

**Files:**
- Create: `test-platform-v2/frontend/src/pages/missions/__tests__/ScenariosPage.test.tsx`
- Modify: `test-platform-v2/frontend/src/pages/missions/scenarios.tsx`
- Modify: `test-platform-v2/frontend/src/api/scenarios.ts`

- [ ] **Step 1: Write the failing mount/request test**

Render `/missions/3/scenarios`, resolve one scenario, and assert `fetchMissionScenarios` runs once with mission id `3` and an `AbortSignal`.

- [ ] **Step 2: Run the test and verify the failure**

Run: `npm test -- --run src/pages/missions/__tests__/ScenariosPage.test.tsx`

Expected: FAIL because `loading=false` retriggers the effect and no signal reaches the API.

- [ ] **Step 3: Implement the same reload contract**

Add `reloadVersion`, change the effect dependencies to `[missionId, reloadVersion]`, pass `signal`, and make the API accept optional AbortSignal.

- [ ] **Step 4: Verify both mission pages together**

Run: `npm test -- --run src/pages/missions/__tests__/ScopePage.test.tsx src/pages/missions/__tests__/ScenariosPage.test.tsx`

Expected: PASS; two files, no repeated request timeout.

### Task 3: Worker Capability List Contract

**Files:**
- Modify: `test-platform-v2/backend/tests/aitde/v34/test_worker_registry.py`
- Modify: `test-platform-v2/backend/app/modules/aitde/workflow/repository.py`
- Modify: `test-platform-v2/backend/app/modules/aitde/workflow/service.py`
- Modify: `test-platform-v2/frontend/src/api/runtime.ts`

- [ ] **Step 1: Write failing list and query-count assertions**

Register two Workers with different capabilities, attach a SQLAlchemy statement listener after setup, call `service.list_workers`, assert each item includes the correct capability array, and assert only one SELECT touches `worker_capabilities`.

- [ ] **Step 2: Run the registry tests and verify the failure**

Run: `python -m pytest tests/aitde/v34/test_worker_registry.py -q`

Expected: FAIL because list items have no `capabilities` field.

- [ ] **Step 3: Add one bulk repository query**

Implement `list_worker_capabilities_by_worker_ids(db, worker_ids) -> dict[int, list[str]]` with one ordered `SELECT worker_id, capability WHERE worker_id IN (...)`; assemble every list row with the returned array. Make register/get/status responses use the same always-present field contract.

- [ ] **Step 4: Verify the registry contract**

Run: `python -m pytest tests/aitde/v34/test_worker_registry.py -q`

Expected: PASS and exactly one capability SELECT for list serialization.

### Task 4: Managed Worker Heartbeat Loop

**Files:**
- Create: `test-platform-v2/backend/app/modules/aitde/workflow/worker_heartbeat.py`
- Create: `test-platform-v2/backend/tests/aitde/v34/test_worker_heartbeat.py`
- Modify: `test-platform-v2/deploy/aitde-runtime/scripts/start-worker.sh`
- Modify: `test-platform-v2/deploy/aitde-runtime/.env.example`
- Modify: `test-platform-v2/deploy/aitde-runtime/README.md`

- [ ] **Step 1: Write failing heartbeat lifecycle tests**

Test payload normalization, immediate first send, retry after a simulated `httpx.ConnectError`, and clean stop after an injected stop event. Assert the environment parser defaults to 60 seconds and rejects intervals at or above the 180-second offline threshold.

- [ ] **Step 2: Run the focused heartbeat tests and verify the failure**

Run: `python -m pytest tests/aitde/v34/test_worker_heartbeat.py -q`

Expected: FAIL because the module does not exist.

- [ ] **Step 3: Implement the minimal async loop**

Create a frozen config dataclass, JSON heartbeat payload, `httpx.AsyncClient.post` with optional bearer token, envelope validation, retry logging, and a stop-aware interval wait. Keep the default at 60 seconds and validate `1 <= interval < 180`.

- [ ] **Step 4: Bind heartbeat and Temporal Worker lifecycles**

Update `start-worker.sh` to start the heartbeat module and gateway as child processes, trap INT/TERM/EXIT, and terminate/wait both children. Preserve `ZONE`, `CAPS`, `BACKEND_URL`, `API_TOKEN`, `WORKER_KEY`, and `TEMPORAL_TASK_QUEUE` compatibility.

- [ ] **Step 5: Verify lifecycle tests and script syntax/static contract**

Run: `python -m pytest tests/aitde/v34/test_worker_heartbeat.py -q`

Expected: PASS.

Run: `python -m pytest tests/test_deploy_contract.py -q` if the existing deploy contract suite covers this path; otherwise record Windows Bash runtime unavailability and validate the launcher in CI/Linux.

### Task 5: Runtime and Onboarding Feedback

**Files:**
- Create: `test-platform-v2/frontend/src/pages/runtime/components/__tests__/WorkerHealthTable.test.tsx`
- Create: `test-platform-v2/frontend/src/pages/runtime/__tests__/RuntimeAdminPage.test.tsx`
- Modify: `test-platform-v2/frontend/src/pages/runtime/components/WorkerHealthTable.tsx`
- Modify: `test-platform-v2/frontend/src/pages/runtime/index.tsx`
- Modify: `test-platform-v2/frontend/src/pages/onboarding/index.tsx`
- Modify: `test-platform-v2/frontend/src/pages/onboarding/__tests__/OnboardingPage.test.tsx`

- [ ] **Step 1: Write failing UI contract tests**

Assert an offline Worker renders its real capabilities, recovery explanation and a “重新检查” action; assert a Runtime API error renders an alert and retry; assert baseline-ready/durable-blocked onboarding says the durable capability is optional and does not block the current baseline.

- [ ] **Step 2: Run the focused tests and verify the failures**

Run: `npm test -- --run src/pages/runtime src/pages/onboarding/__tests__/OnboardingPage.test.tsx`

Expected: FAIL on missing recovery/retry text and old durable status wording.

- [ ] **Step 3: Implement the four-state UI**

Add a PageHeader refresh button and `loadError` state, show an offline guidance band above the table, make empty/error states actionable, and keep drain/disable limited to ONLINE. Catch mutation failures and show the server message. Update the onboarding badge and explanatory sentence.

- [ ] **Step 4: Verify focused frontend tests**

Run: `npm test -- --run src/pages/missions/__tests__/ScopePage.test.tsx src/pages/missions/__tests__/ScenariosPage.test.tsx src/pages/runtime src/pages/onboarding/__tests__/OnboardingPage.test.tsx`

Expected: PASS.

### Task 6: Gates, Browser Evidence, and Local Commits

**Files:**
- Create: `work-logs/evidence/batch-228-runtime-ui-stability/README.md`
- Create: `work-logs/batch-228-runtime-ui-stability-qa-report.md`
- Create: `work-logs/batch-228-runtime-ui-stability-leader-verdict.md`
- Modify: `work-logs/kanbans/DEV-batch-228-runtime-ui-stability.md`

- [ ] **Step 1: Run scoped and full gates**

Frontend: `npm ci`, focused Vitest, `npm test -- --reporter=dot`, `npm run typecheck`, `npm run lint`, `npm run build`.

Backend: focused Pytest, `python -c "import app.main"`, `python -m ruff check app --select F821`, Alembic single-head/revision tests, then full `python -m pytest -q`.

Repository: `pwsh scripts/git/scan-common-bugs.ps1`, `pwsh scripts/git/dev-gate.ps1 -RepositoryPath (Get-Location).Path`, and `pwsh scripts/git/audit-cconditions.ps1 -RequireLatestBatch`.

- [ ] **Step 2: Run browser regression on isolated ports**

Start backend on 8028 and frontend on 5198. Verify onboarding wording, Worker offline/online states, and mission scope/scenario Network requests at 1440×900, 768×1024, and 390×844. Expected: no horizontal overflow, no console/page errors, and one effective GET per page open or explicit reload.

- [ ] **Step 3: Record evidence and update the kanban**

Write exact command, exit code, pass/fail counts, screenshots, request counts, known baseline warnings, production-deployment boundary, and retro card into the evidence index and QA report. Keep Leader decision conditional until required checks and final PR audit complete.

- [ ] **Step 4: Commit each completed slice locally**

Stage only files from the completed slice, inspect `git diff --cached --name-status`, and create conventional `fix(batch-228): ...` commits. Do not push.

- [ ] **Step 5: Stop for the Agent Team total confirmation**

Present the exact branch, target, changed files, test results and risk. Ask: `确认推送 fix/batch-228-runtime-ui-stability、创建 Draft PR，并在 required checks 通过后合并到 main？` Only an explicit confirmation authorizes push, PR creation and later merge.
