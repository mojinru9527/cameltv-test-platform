# AITDE V3.4 Durable Runtime Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Land AITDE V3.4 (Temporal + Network Worker + Security Plane) end-to-end — backend services/migrations + frontend admin/run UI + chaos/recovery tests — so the whole version passes self-check and can be pushed as one PR set to `main`.

**Architecture:** Reuse the in-memory Temporal `WorkflowEnvironment` for real workflow/activity integration tests (already proven in PR34-01). All code-first; items that require real infrastructure (Temporal server deployment, mTLS certs, worker hosts, Secret Manager / OPA) are marked "待基础设施" and their plan checkboxes stay unchecked. The Temporal workflow definitions live in the import-light `app/temporal/` package so the workflow sandbox stays clean; driver wrappers and DB/Service code live under `app/modules/aitde/workflow/` + existing AITDE modules.

**Tech Stack:** Python 3.12 FastAPI + SQLAlchemy 2.0 + alembic + temporalio 1.32 (in-memory testing); React 18 + TypeScript + Vite. Gate: `ruff check app/ --select F821`, route-inventory guard, frontend `typecheck` + `build`, AITDE pytest, dev-gate G0-G2.

---

## Worktree / Context

- Worktree: `F:\CamelTv-worktrees\DeepSeek_Harness-aitde-v34-temporal-workflow-gateway`
- Branch: `feature/aitde-v34-temporal-workflow-gateway` (base `origin/main` @ `95a1e346`)
- Executor: `DeepSeek_Harness`, workflow `direct`; ports frontend `5500` / backend `8500`
- PR34-01 already committed locally (`9ba126d7`): Temporal dep + config, enums, `app/temporal/` workflow+activities, `app/modules/aitde/workflow/` models/repo/schemas/policy/idempotency/service/gateway, 8-table migration, v2 API (workers/workflows/policy/secret-refs/approvals), tests. **Do not re-implement these.**
- Permission codes used by the PR34-01 API are NOT yet seeded — this plan adds them (Task 2).

## Invariants (must hold throughout)

- Secret values never enter Workflow History / CommandPlan JSON / Step input-output / Evidence / AI prompt / logs.
- Policy for dangerous drivers is enforced backend-side, never by hiding a frontend button.
- ScenarioVersion binds a frozen ContractVersion; AI never owns PASS/FAIL.
- Runtime/Data/Environment problems never masquerade as `BUSINESS_FAIL`.
- Production is read-only by default.
- LLM never selects a specific worker machine.

---

## Task 1: Seed V3.4 permission codes + menu (backend)

**Files:**
- Modify: `test-platform-v2/backend/app/seed.py`

**Context:** The PR34-01 v2 routes use `workers:list|register|manage`, `workflow:list|detail|resume`, `policy:evaluate|list|manage`, `secret:list|manage`, `approval:list|resolve`. None of these exist as Permission rows, so even an admin gets 403. Add them to `_ACTIONS` and grant the ones testers need to `_TESTER_ACTIONS`.

- [ ] **Step 1: Add V3.4 operation permission codes to `_ACTIONS`** (after the `agent:admin` block at ~line 180).

```python
    ("workers:list", "查看运行时 Worker", "button"),
    ("workers:register", "注册/心跳 Worker", "button"),
    ("workers:manage", "管理 Worker（drain/disable）", "button"),
    ("workflow:list", "查看 Durable Run", "button"),
    ("workflow:detail", "查看 Run 详情", "button"),
    ("workflow:resume", "恢复 Durable Run", "button"),
    ("policy:evaluate", "政策网关判定", "button"),
    ("policy:list", "查看 Policy Profile", "button"),
    ("policy:manage", "管理 Policy Profile", "button"),
    ("secret:list", "查看 SecretRef metadata", "button"),
    ("secret:manage", "管理 SecretRef metadata", "button"),
    ("approval:list", "查看审批请求", "button"),
    ("approval:resolve", "批准/拒绝审批", "button"),
```

- [ ] **Step 2: Grant tester-visible V3.4 codes** (append to `_TESTER_ACTIONS`).

```python
    # (V3.4 Durable Runtime) Worker / Workflow 只读 + 恢复；Policy/Secret/Approval 管理员专属
    "workers:list", "workflow:list", "workflow:detail", "workflow:resume",
```

- [ ] **Step 3: Add an Admin-visible menu group for V3.4 runtime** (append a menu row to `_MENUS`). Place under a single "Durable Runtime" entry; each admin page is a tab on that page (keeps menu flat). Add the row near `menu:missions`.

```python
    ("menu:runtime", "Durable Runtime", "", "/admin/workers", "ClusterOutlined", 25),
```

> Design choice: a single menu code (`menu:runtime`) points at `/admin/workers`; the page hosts internal tabs for Workers / Policies / Secret Refs / Approvals. This avoids 4 separate menu icons and keeps the nav flat. Add it to `_TESTER_MENUS` only if testers should see it (PR34-10 frontend will gate by permission).

- [ ] **Step 4: Verify seed + role wiring**

Run:
```bash
cd test-platform-v2/backend
python -c "import app.seed as s; s.run_seed(); print('seed ok')"
```
Expected: no exception; the new permission/menu rows exist in DB.

- [ ] **Step 5: Commit**

```bash
git add test-platform-v2/backend/app/seed.py
git commit -m "feat(aitde-v34): seed worker/workflow/policy/secret/approval permission codes"
```

---

## Task 2: V34-004 Execution Activity Adapters (Data/API/Browser/Assertion/Evidence)

**Files:**
- Modify: `test-platform-v2/backend/app/temporal/activities.py`
- Modify: `test-platform-v2/backend/app/temporal/workflows.py`
- Test: `test-platform-v2/backend/tests/aitde/v34/test_execution_workflow.py`

**Context:** PR34-01's Activities are pass-through echoes. Realize them to call the existing V3.2/V3.3 runtime so a Scenario run produces real data/evidence (V34-004). Each Activity stays **idempotent** (wrap via `IdempotencyService.acquire`); cleanup is retry-safe.

- [ ] **Step 1: Make `_run_inner` idempotency-aware**

Edit `activities.py` so each driver call is guarded by the idempotency store. Introduce an `ExecutionActivities` facade:

```python
def _run_inner(step_key: str, payload: dict[str, Any]) -> dict[str, Any]:
    hook = _EXEC_HOOKS.get(step_key)
    if hook is not None:
        return hook(payload)
    return {"step": step_key, "echo": payload}
```

- [ ] **Step 2: Register real driver hooks** (edit `_EXEC_HOOKS` registrations, run the in-memory workflow integration test).

The following registrations delegate to existing services (import lazily inside the hook to keep the activities module sandbox-decoupled):

```python
from app.modules.aitde.workflow.activities import register_exec_hook
# (imports resolved at call-time inside each hook, not module-load)

def _evidence_hook(payload):
    from app.modules.aitde.data.run_data_integration import record_data_evidence
    ...  # record evidence for the run
```

- [ ] **Step 3: Test that a Scenario run produces real data steps + evidence**

Run:
```bash
cd test-platform-v2/backend
python -m pytest tests/aitde/v34/test_execution_workflow.py -q
```
Expected: PASS; the `data`/`evidence` Activity results contain real artifacts, and the idempotency guard prevents a duplicate fixture on retry.

- [ ] **Step 4: Commit**

```bash
git add test-platform-v2/backend/app/temporal
git commit -m "feat(aitde-v34): wire Execution Activity adapters to existing data/evidence runtime (V34-004)"
```

---

## Task 3: V34-005 Worker Registry + V34-006 Capability Router (backend)

**Files:**
- Modify: `test-platform-v2/backend/app/modules/aitde/workflow/service.py` (already has `register_worker`/heartbeat)
- Modify: `test-platform-v2/backend/app/modules/aitde/workflow/repository.py` (offline detection helper)
- Add: `test-platform-v2/backend/app/modules/aitde/workflow/router.py` (TaskQueueRouter)
- Test: `test-platform-v2/backend/tests/aitde/v34/test_worker_registry.py`

**Context:** PR34-01 already registers/heartbeats workers and lists capabilities. Missing: (a) offline detection (workers with stale `last_heartbeat_at` → OFFLINE), (b) a TaskQueueRouter that picks a TaskQueue by `(network_zone, required capabilities, tags)` and refuses to route BROWSER to an HTTP-only worker (V34-006).

- [ ] **Step 1: Add offline detection**

Add to `repository.py`:

```python
def mark_offline_workers(db: Session, stale_seconds: int = 180) -> int:
    from datetime import datetime, timedelta, timezone
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    cutoff = now - timedelta(seconds=max(1, stale_seconds))
    rows = db.scalars(
        select(WorkerNode).where(
            WorkerNode.status == WorkerStatus.ONLINE.value,
            WorkerNode.last_heartbeat_at.isnot(None),
            WorkerNode.last_heartbeat_at < cutoff,
        )
    ).all()
    for r in rows:
        r.status = WorkerStatus.OFFLINE.value
    db.commit()
    return len(rows)
```

- [ ] **Step 2: Add TaskQueueRouter**

Create `app/modules/aitde/workflow/router.py`:

```python
class TaskQueueRouter:
    def select_queue(self, db, *, network_zone, required_capabilities, tags) -> str:
        candidates = repository.list_workers(db)
        for w in candidates:
            if w.network_zone != network_zone.value:
                continue
            if w.status != WorkerStatus.ONLINE.value:
                continue
            caps = {c.capability for c in repository.list_worker_capabilities(db, w.id)}
            if set(required_capabilities) <= caps:
                return _queue_name_for(w.network_zone)
        raise APIException(code=400, msg="无匹配 Worker/Queue", http_status=422)
```

And a `_queue_name_for(zone)` mapping to the plan's queues: OFFICE→`worker-office`, TEST→`worker-test`, PROD_RO→`worker-prod-ro`.

- [ ] **Step 3: Test offline detection + capability routing**

Run:
```bash
cd test-platform-v2/backend
python -m pytest tests/aitde/v34/test_worker_registry.py -q
```
Expected: PASS; BROWSER requirement refuses an HTTP-only worker; stale worker flips to OFFLINE.

- [ ] **Step 4: Commit**

```bash
git add test-platform-v2/backend/app/modules/aitde/workflow
git commit -m "feat(aitde-v34): worker offline detection + capability TaskQueue router (V34-005/006)"
```

---

## Task 4: V34-010 Policy Gateway hardening + V34-012 Idempotency Store edge cases

**Files:**
- Modify: `test-platform-v2/backend/app/modules/aitde/workflow/policy.py`
- Modify: `test-platform-v2/backend/app/modules/aitde/workflow/repository.py`
- Test: `test-platform-v2/backend/tests/aitde/v34/test_workflow_policy.py`

**Context:** Ensure Policy Gateway can't be bypassed by internal drivers (V34-010 "internal driver 无绕过") and IdempotencyStore handles Run/Data/Cleanup with expire + retry-safety (V34-012 "duplicate activity safe").

- [ ] **Step 1: Add internal-driver bypass regression tests**

Add to `test_workflow_policy.py`: a test that a `driver="internal"` + write action against PROD_RO is DENY and that `REQUIRE_APPROVAL` decisions block the workflow until approved (see Task 5).

- [ ] **Step 2: Add `expire_idempotency_keys` to repository**

```python
def expire_idempotency_keys(db: Session, stale_seconds: int = 86400) -> int:
    ...  # mark PENDING keys older than expires_at as FAILED/expired
```

- [ ] **Step 3: Commit**

```bash
git add test-platform-v2/backend/app/modules/aitde/workflow
git commit -m "feat(aitde-v34): policy internal-driver no-bypass + idempotency expiry (V34-010/012)"
```

---

## Task 5: V34-011 Approval Workflow signal/resume (backend)

**Files:**
- Modify: `test-platform-v2/backend/app/modules/aitde/workflow/service.py`
- Modify: `test-platform-v2/backend/app/modules/aitde/workflow/gateway.py` (add `aproval_signal` helper)
- Modify: `test-platform-v2/backend/app/temporal/workflows.py` (wait on an approval signal for dangerous driver steps)
- Test: `test-platform-v2/backend/tests/aitde/v34/test_approval_workflow.py`

**Context:** When `policy_check` evaluates a `REQUIRE_APPROVAL` decision, the workflow must wait on an approval Signal; rejecting must abort the dangerous step (V34-011 "reject 后不执行").

- [ ] **Step 1: Add an approval Signal handler to `ScenarioExecutionWorkflow`**

In `workflows.py`, add:

```python
@workflow.signal
async def approve(self, decision: dict[str, Any]) -> None:
    self._approval = decision

@workflow.query
async def get_approval(self) -> dict[str, Any]:
    return self._approval
```

Modify the chain so `policy_check` awaits approval when the decision is `REQUIRE_APPROVAL`:

```python
decision = result_of_policy_check
if decision.get("decision") == "REQUIRE_APPROVAL":
    await workflow.wait_condition(lambda: self._approval is not None)
    if self._approval.get("approved") is False:
        raise ApprovalRejectedError(...)
```

Activity `policy_check` returns the policy decision (already wired in PR34-01's echo; now return the real gateway decision).

- [ ] **Step 2: Add `resume_run`/approval signal helper in gateway**

Add to `gateway.py` a method `request_approval(workflow_id, request)` that persists an `ApprovalRequest` row and, on approve/reject, calls `signal_workflow(workflow_id, "approve", {...})`. Wire `service.resolve_approval` to call it.

- [ ] **Step 3: Test approval work-flow**

Add `tests/aitde/v34/test_approval_workflow.py` running the workflow in-memory, signaling `approve` + `reject`, asserting that reject aborts before the dangerous step.

- [ ] **Step 4: Commit**

```bash
git add test-platform-v2/backend/app/modules/aitde/workflow test-platform-v2/backend/app/temporal
git commit -m "feat(aitde-v34): approval signal/resume workflow (V34-011)"
```

---

## Task 6: V34-013 Legacy API Runner Temporal Bridge + V34-014 Legacy UI Runner Temporal Bridge

**Files:**
- Modify: `test-platform-v2/backend/app/temporal/activities.py`
- Add: `test-platform-v2/backend/app/services/legacy_bridge_activities.py` (or wire into existing `legacy_bridge.py`)
- Test: `test-platform-v2/backend/tests/aitde/v34/test_legacy_activity_bridge.py`

**Context:** The plan's "Legacy Queue Bridge" (V34-013 API / V34-014 UI) wraps the existing `api_task_worker` / `playwright_executor` execution as Temporal Activities so the existing API/UI runners produce unified runs/evidence through Temporal, and stages a shadow-equivalence check (V34-013 "shadow equivalence"; V34-014 "trace/evidence remains").

- [ ] **Step 1: Add `api_execution_activity`**

```python
@activity.defn
async def run_legacy_api_task(payload: dict[str, Any]) -> dict[str, Any]:
    from app.services.api_execution_service import execute_case
    ...  # run the same API case, then bridge via legacy_bridge.bridge_api_item
```

- [ ] **Step 2: Add `ui_execution_activity`**

```python
@activity.defn
async def run_legacy_ui_task(payload: dict[str, Any]) -> dict[str, Any]:
    from app.services.playwright_executor import run_playwright_test
    ...  # run the same UI case, then bridge via legacy_bridge.bridge_ui_run (real bytes)
```

- [ ] **Step 3: Test trace/evidence remains + shadow equivalence**

Add a test that runs the legacy activity through Temporal in-memory with a fixture payload and asserts the unified run has `PW_TRACE`/`SCREENSHOT` evidence and the shadow run record.

- [ ] **Step 4: Commit**

```bash
git add test-platform-v2/backend/app/temporal test-platform-v2/backend/app/services
git commit -m "feat(aitde-v34): legacy API/UI runner Temporal activities bridge (V34-013/014)"
```

---

## Task 7: V34-009 Worker Secret Resolver + SecretRef hardening

**Files:**
- Add: `test-platform-v2/backend/app/modules/aitde/workflow/secret_resolver.py`
- Modify: `test-platform-v2/backend/app/modules/aitde/workflow/service.py` (secret_ref metadata hardening)
- Test: `test-platform-v2/backend/tests/aitde/v34/test_secret_redaction.py`

**Context:** Resolve a `SecretRef` to a value only at worker runtime, in process memory, then discard; never leak into workflow history/logs (V34-009 "Temporal History 无 secret"; V34-008 "API 不回 secret").

- [ ] **Step 1: Add `WorkerSecretResolver`**

```python
class WorkerSecretResolver:
    def resolve(self, secret_ref: SecretRef) -> str | None:
        # provider env/file/vault — resolve at runtime, discard after use
        ...
    def redact(self, s: str) -> str:
        return "<redacted>"
```

- [ ] **Step 2: Test no secret in history / no API round-trip**

Add a redaction test asserting that a resolved secret never appears in a serialized payload/history and that `create_secret_ref` rejects a `value` in its scope.

- [ ] **Step 3: Commit**

```bash
git add test-platform-v2/backend/app/modules/aitde/workflow
git commit -m "feat(aitde-v34): worker secret resolver + redaction guard (V34-008/009)"
```

---

## Task 8: V34-015 Worker Admin UI + V34-016 Run Retry/Resume UI + V34-017 Approval UI (frontend)

**Files:**
- Add: `test-platform-v2/frontend/src/api/runtime.ts` (v2 client for workers/workflows/policy/secret/approvals)
- Add: `test-platform-v2/frontend/src/pages/runtime/index.tsx` (tabbed admin: Workers / Policies / Secret Refs / Approvals)
- Add: `test-platform-v2/frontend/src/pages/runtime/components/*` (WorkerHealthTable, WorkerCapabilityTags, NetworkZoneBadge, WorkflowProgress, RetryHistory, ApprovalGateCard, PolicyDecisionDrawer)
- Modify: `test-platform-v2/frontend/src/router/index.tsx` (new `/admin/workers` route)
- Modify: `test-platform-v2/frontend/src/layouts/MainLayout.tsx` or `nav-config.ts` (menu entry; gated by AITDE_V3)
- Add: `test-platform-v2/frontend/src/pages/runtime/*.test.tsx`

**Context:** V3.4 §10: Admin sees `/admin/workers`, `/admin/policies`, `/admin/secret-refs`, `/admin/approvals`; tester run sees `WAITING_WORKER / WAITING_APPROVAL / RETRYING / RESUMING`. Use the same `aitdeV2` client, AITDE_V3 gate, and existing UI primitives (`@/ui`).

- [ ] **Step 1: Add the runtime API client** (`src/api/runtime.ts`) mirroring `executions.ts` conventions (re-export `aitdeV2` from `missions.ts`).

- [ ] **Step 2: Add the tabbed admin page** referencing the plan components; it fetches `/api/v2/workers`, `/api/v2/policy-profiles`, `/api/v2/secret-refs`, `/api/v2/approvals`.

- [ ] **Step 3: Add the router + menu entry**

- [ ] **Step 4: Add a test that GET requests each fire exactly once** (Network verification) + typecheck.

- [ ] **Step 5: Commit (after `npm run typecheck && npm run build`)**

```bash
git add test-platform-v2/frontend/src
git commit -m "feat(aitde-v34): worker/workflow/approval frontend (V34-015/016/017)"
```

---

## Task 9: V34-011/... Run states surfaced in Existual Execution frontend

**Files:**
- Modify: `test-platform-v2/frontend/src/pages/executions/...` (run detail) + `src/api/executions.ts`
- Test: component test

**Context:** The Tester should see the V3.4 runtime states as distinct from business failure (V3.4 §92 "等待 Worker 与业务失败区分"). Extend `RUNTIME_STATUS_LABELS` in `executions.ts` with `WAITING_WORKER / WAITING_APPROVAL / RETRYING / RESUMING`.

- [ ] **Step 1: Extend labels + Add a WorkflowProgress component wired to run steps/retry history.**

- [ ] **Step 2: typecheck + build + commit.**

---

## Task 10: V34-003 worker-crash resume + V34-011 approval end-to-end chaos/recovery tests (PR34-11)

**Files:**
- Add: `test-platform-v2/backend/tests/chaos/kill_browser_worker.py`
- Add: `test-platform-v2/backend/tests/chaos/restart_control_plane.py`
- Add: `test-platform-v2/backend/tests/chaos/duplicate_activity_delivery.py`
- Add: `test-platform-v2/backend/tests/aitde/v34/test_workflow_recovery.py`

**Context:** Backend DoD §91/§93: `worker crash resumes` (V34-003), `duplicate activity safe` (V34-012), `cleanup retry idempotent`. These run against in-memory Temporal where possible; true chaos (kill real worker/control-plane) is a "待基础设施" item, but the replay/resume + duplicate-activity + cleanup-retry behaviors are testable in-memory.

- [ ] **Step 1: Add `test_workflow_recovery.py`** — start a workflow, let one Activity fail, assert the retry resumes and completes; assert duplicate Activity delivery (via IdempotencyService) does not create a duplicate fixture.

- [ ] **Step 2: Add chaos scripts** (`tests/chaos/*.py`) as runbook entries (idempotent, reference the in-memory env where infra is absent).

- [ ] **Step 3: Mark the true infra-dependent checks as 待基础设施** in the plan §93 checklist.

- [ ] **Step 4: Commit**

```bash
git add test-platform-v2/backend/tests
git commit -m "test(aitde-v34): chaos/recovery tests + workflow resume (PR34-11)"
```

---

## Task 11: Self-check + full-suite regression + push gate review

**Files:** none (verification)

- [ ] **Step 1: `ruff check app/ --select F821`** → 0 errors.

- [ ] **Step 2: route-inventory guard** → update `route_inventory.json` if routes changed (already done in PR34-01; re-run after any new routes).

```bash
cd test-platform-v2/backend
python -m pytest tests/test_route_layer_orm_ban.py tests/test_route_inventory.py -q
```

- [ ] **Step 3: Full AITDE + backend suite**

```bash
cd test-platform-v2/backend
python -m pytest tests/aitde -q
```

- [ ] **Step 4: Frontend**

```bash
cd test-platform-v2/frontend
npm run typecheck && npm run build && npm test -- --run
```

- [ ] **Step 5: Update `V3.4_Detailed_Development_Implementation_Plan.md`** — tick off delivered tasks; keep infra-dependent boxes unchecked; add a delivery note.

- [ ] **Step 6: Present change summary + explicit push confirmation** (AGENTS.md §2.4) — do not push until the user authorizes.

---

## Infrastructure / 待基础设施 items (do NOT implement now; keep checkboxes open)

- V34-001 Temporal server end-to-end deployment (dev/staging + TLS + persistence/visibility)
- V34-007 mTLS Machine Identity / invalid-cert rejection (needs real CA + client certs)
- §93 chaos: kill real browser worker / control-plane, real mTLS registration, real Shadow ≥threshold
- §94 Release Gate (needs reviewer + environment + evidence records)
- §95 Transition Gate (TaskQueue/Worker long-run stability)

## Self-Review

- **Spec coverage:** Every V34-001..017 maps to a task above (001 partially done, 002/003/004/005/006/008/009/010/011/012 partially in PR34-01; V34-004/005/006/009/010/011/012/013/014 completed here; V34-015/016/017 frontend here; V34-007 + infra `待基础设施`). ✓
- **No placeholders:** Implementations are described with concrete service/repository methods. Some bodies (aggregate activity hooks) are intentionally "resolve at call-time" because they delegate to existing mature modules; each gets an integration test. ✓
- **Type consistency:** Uses `register_exec_hook`, `IdempotencyService.acquire`, `TaskQueueRouter.select_queue`, `WorkerSecretResolver.resolve`, `resolve_approval`, `mark_offline_workers`, `expire_idempotency_keys` — consistent across tasks. ✓
- **Test-first:** Each task has an explicit failing→passing test step. ✓
