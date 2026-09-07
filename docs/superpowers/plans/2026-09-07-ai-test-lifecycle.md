# AI Test Lifecycle Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Connect requirement analysis, three classified case types, per-case execution evidence, defects, and retests into one truthful VersionTask/Mission lifecycle.

**Architecture:** Keep VersionTask as the release-level root and link phase-specific AITDE Missions through a foreign key. Extend existing scenario versions with classification metadata, reuse ExecutionRun/EvidenceArtifact/parent_run_id for attempts and retests, and attach defects directly to failed AITDE runs. A single mission lifecycle query supplies the overview without frontend N+1 requests.

**Tech Stack:** FastAPI, SQLAlchemy 2, Alembic, Pydantic v2, React, TypeScript, TanStack Query, shadcn/ui, Vitest, Pytest.

---

### Task 1: Persist lifecycle identity and case classification

**Files:**
- Modify: `test-platform-v2/backend/app/modules/aitde/mission/models.py`
- Modify: `test-platform-v2/backend/app/modules/aitde/mission/schemas.py`
- Modify: `test-platform-v2/backend/app/modules/aitde/mission/service.py`
- Modify: `test-platform-v2/backend/app/modules/aitde/mission/mapper.py`
- Modify: `test-platform-v2/backend/app/modules/aitde/scenario/models.py`
- Modify: `test-platform-v2/backend/app/modules/aitde/scenario/schemas.py`
- Modify: `test-platform-v2/backend/app/modules/aitde/scenario/repository.py`
- Create: `test-platform-v2/backend/alembic/versions/20260914_b232_ai_test_lifecycle.py`
- Test: `test-platform-v2/backend/tests/aitde/test_ai_test_lifecycle.py`

- [ ] Write failing tests proving same-project VersionTask links are accepted, cross-project links fail, and ScenarioCandidate requires valid case/role/module metadata.
- [ ] Run `pytest tests/aitde/test_ai_test_lifecycle.py -q` and confirm the new assertions fail.
- [ ] Add `Mission.version_task_id`; add scenario version `case_type`, `requirement_role`, `module_key`; expose them through schemas and mappers.
- [ ] Add a single-head migration after `20260913_b231_traceability_truth`; use nullable/default historical values so old rows remain readable.
- [ ] Run the focused tests and Alembic head check until green.
- [ ] Commit only Task 1 files with `feat(batch-232): link missions and classify cases`.

### Task 2: Enforce AI scenario completeness

**Files:**
- Modify: `test-platform-v2/backend/app/modules/aitde/intelligence/prompts/scenario_design_v1.txt`
- Modify: `test-platform-v2/backend/app/modules/aitde/intelligence/provider.py`
- Modify: `test-platform-v2/backend/app/modules/aitde/scenario/service.py`
- Test: `test-platform-v2/backend/tests/aitde/test_ai_test_lifecycle.py`

- [ ] Add failing tests for an AI response missing classification, deterministic output classification, and Mission scenario list/detail metadata.
- [ ] Run the tests and confirm validation fails before persistence.
- [ ] Update the prompt’s exact JSON shape and deterministic provider defaults; keep AI Oracle trust behavior unchanged.
- [ ] Return the three new fields from scenario list/detail APIs.
- [ ] Run focused scenario and provider tests until green.
- [ ] Commit with `feat(batch-232): require traceable scenario metadata`.

### Task 3: Link failed executions to defects and retests

**Files:**
- Modify: `test-platform-v2/backend/app/models/defect.py`
- Modify: `test-platform-v2/backend/app/schemas/defect.py`
- Modify: `test-platform-v2/backend/app/api/v2/executions.py`
- Create: `test-platform-v2/backend/app/modules/aitde/execution/defects.py`
- Modify: `test-platform-v2/backend/alembic/versions/20260914_b232_ai_test_lifecycle.py`
- Test: `test-platform-v2/backend/tests/aitde/test_ai_test_lifecycle.py`

- [ ] Add failing tests for failed-run defect creation, idempotent reuse, cross-project rejection, and retry `parent_run_id` preservation.
- [ ] Run focused tests and confirm the defect endpoint is absent.
- [ ] Add nullable indexed `Defect.aitde_run_id`, service validation, and `POST /runs/{run_id}/defects`.
- [ ] Reuse an existing open defect for the same run and include `aitde_run_id` in Defect schemas.
- [ ] Run focused execution/defect tests until green.
- [ ] Commit with `feat(batch-232): connect run defects and retests`.

### Task 4: Add one-query Mission lifecycle summary

**Files:**
- Create: `test-platform-v2/backend/app/modules/aitde/mission/lifecycle.py`
- Modify: `test-platform-v2/backend/app/api/v2/missions.py`
- Test: `test-platform-v2/backend/tests/aitde/test_ai_test_lifecycle.py`

- [ ] Seed a Mission with sources, scope, contract, classified scenarios, runs, evidence, a defect and a retry; write an expected lifecycle response test.
- [ ] Run the test and confirm `GET /api/v2/missions/{id}/lifecycle` is missing.
- [ ] Implement set-based aggregate queries for stage counts, case/role counts, sibling phase Missions, and per-scenario execution facts.
- [ ] Derive gaps and retest state from persisted facts; emit UNCLASSIFIED for legacy rows.
- [ ] Prove query count is bounded independently of scenario count and run tenant isolation tests.
- [ ] Commit with `feat(batch-232): expose mission lifecycle facts`.

### Task 5: Replace static overview with live facts

**Files:**
- Modify: `test-platform-v2/frontend/src/api/missions.ts`
- Modify: `test-platform-v2/frontend/src/pages/missions/overview.tsx`
- Create: `test-platform-v2/frontend/src/pages/missions/__tests__/OverviewPage.test.tsx`

- [ ] Write failing component tests for phase labels, six real stages, all three case types, missing classifications, failed case evidence/defect/retest states, and error retry.
- [ ] Run the focused Vitest and confirm failures against the static overview.
- [ ] Add lifecycle types/client and one TanStack Query using its AbortSignal.
- [ ] Render responsive stage, coverage, and per-case sections with Chinese status labels and semantic tokens.
- [ ] Run focused Vitest, typecheck and build until green.
- [ ] Commit with `feat(batch-232): show truthful mission lifecycle`.

### Task 6: Verify and prepare delivery

**Files:**
- Create: `work-logs/evidence/batch-232-ai-test-lifecycle/README.md`
- Create: `work-logs/batch-232-ai-test-lifecycle-qa-report.md`
- Create: `work-logs/batch-232-ai-test-lifecycle-leader-verdict.md`
- Modify: `work-logs/kanbans/DEV-batch-232-ai-test-lifecycle.md`

- [ ] Run backend F821, import, focused and full Pytest, Alembic single-head checks; record commands, exits and failure sets.
- [ ] Run frontend focused/full Vitest, typecheck and build; record commands, exits and failure sets.
- [ ] Start backend on 8015 and frontend on 5188, verify desktop/tablet/mobile overview with browser screenshots and console/network checks.
- [ ] Complete QA report with real-data anti-fake-success audit and retro card.
- [ ] Keep Leader decision pending until required checks are green per C227-1; complete process writeback and retro card.
- [ ] Present the exact change summary and ask the one total confirmation for push, Draft PR, green-check merge, and production release.
