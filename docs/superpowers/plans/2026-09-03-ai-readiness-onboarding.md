# AI Readiness Onboarding Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build one truthful AI end-to-end onboarding page that collects the six business inputs and separates them from platform-managed AI/Temporal/Worker readiness.

**Architecture:** Extend the existing BusinessOnboarding aggregate instead of creating a second onboarding container. A read-only backend readiness projection composes existing AI health, Temporal configuration, and Worker heartbeat facts; the React page consumes that projection once and leaves process lifecycle to deployment.

**Tech Stack:** FastAPI, SQLAlchemy 2, Alembic, React 19, TypeScript, shadcn/Radix primitives, Tailwind, pytest, Vitest, Playwright.

---

### Task 1: Persist version and requirement context

**Files:**
- Modify: `test-platform-v2/backend/app/models/business_onboarding.py`
- Modify: `test-platform-v2/backend/app/api/v1/onboarding.py`
- Modify: `test-platform-v2/backend/app/services/onboarding_service.py`
- Create: `test-platform-v2/backend/alembic/versions/20260911_business_onboarding_context.py`
- Test: `test-platform-v2/backend/tests/test_version_task.py`

- [ ] Add failing service/API assertions that `version=16.0.0` and `requirement_text` round-trip.
- [ ] Add failing assertion that Step 2 creates a RequirementDocument and binds it to VersionTask.
- [ ] Add the two columns with bounded API validation and a single-head migration.
- [ ] Reuse `requirement_service.create_requirement(..., commit=False)` and pass its id plus `ob.version` to `create_task`.
- [ ] Run `pytest tests/test_version_task.py -q`; expect all tests to pass.
- [ ] Commit only Task 1 files with `feat(batch-227): bind onboarding version and requirement`.

### Task 2: Add a truthful readiness projection

**Files:**
- Modify: `test-platform-v2/backend/app/services/onboarding_service.py`
- Modify: `test-platform-v2/backend/app/api/v1/onboarding.py`
- Test: `test-platform-v2/backend/tests/test_version_task.py`
- Modify: `test-platform-v2/backend/tests/fixtures/route_inventory.json`

- [ ] Add failing tests for AI ok/unknown/error, Temporal disabled/enabled, fresh/stale Worker heartbeats, and baseline versus durable readiness.
- [ ] Implement `get_readiness(db, project_id)` using `ai_config_service.resolve_out`, `temporal_gateway.unavailable`, and Worker repository queries; do not initiate process startup or network probes.
- [ ] Register static `GET /onboarding/readiness` before dynamic onboarding routes and return the standard envelope.
- [ ] Regenerate/update route inventory and run the focused API tests.
- [ ] Commit only Task 2 files with `feat(batch-227): expose AI chain readiness`.

### Task 3: Rebuild the onboarding page around user intent

**Files:**
- Modify: `test-platform-v2/frontend/src/api/versionTask.ts`
- Modify: `test-platform-v2/frontend/src/pages/onboarding/index.tsx`
- Create: `test-platform-v2/frontend/src/pages/onboarding/__tests__/OnboardingPage.test.tsx`

- [ ] Mock API functions and write failing tests for six labels, disabled incomplete submission, one readiness request, platform-managed copy, explicit action labels, and error retry.
- [ ] Extend frontend types and API functions for the two new fields and readiness response.
- [ ] Implement one abortable page load for onboarding list + readiness, stable loading/error states, and a guarded submit/advance state.
- [ ] Render responsive fields and non-nested readiness rows using semantic tokens and Lucide icons.
- [ ] Run the focused Vitest test, then `npm run typecheck`.
- [ ] Commit Task 3 files with `feat(batch-227): simplify AI onboarding readiness UI`.

### Task 4: Verify behavior and finish Agent Team artifacts

**Files:**
- Create: `work-logs/batch-227-ai-readiness-onboarding-qa-report.md`
- Create: `work-logs/batch-227-ai-readiness-onboarding-leader-verdict.md`
- Modify: `work-logs/kanbans/DEV-batch-227-ai-readiness-onboarding.md`
- Create: `work-logs/evidence/batch-227-ai-readiness-onboarding/README.md`

- [ ] Run bug scan, backend F821/import/Alembic/focused/full pytest, frontend install/typecheck/lint/build/focused/full Vitest, and dev-gate; record command and exit code.
- [ ] Start isolated backend `8900` and frontend `5577`, then verify tester login and `/onboarding` with Playwright.
- [ ] Capture desktop, tablet, and mobile screenshots; assert no horizontal overflow, console errors, duplicate GETs, or secret values.
- [ ] Complete QA report with logic audit, real-data/fake-success evidence, CI classification, and retro card.
- [ ] Present the exact change scope and request the single Agent Team confirmation before any push or PR action.
- [ ] After confirmation, push, create Draft PR, audit, wait for required checks, final-audit, complete Leader verdict, mark Ready, and squash merge.

## Self-review

- Spec coverage: six user inputs, platform-managed services, two readiness meanings, requirement binding, accessibility, responsive behavior, and no process startup are each mapped to Tasks 1–4.
- Placeholder scan: no deferred implementation placeholder remains; external runtime availability is intentionally represented as runtime state, not a code TODO.
- Type consistency: backend/frontend use `version`, `requirement_text`, `baseline_ready`, `durable_ready`, and `services` consistently.
