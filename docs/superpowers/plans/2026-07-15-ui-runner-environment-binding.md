# UI Runner Environment Binding Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let a DEV user select a configured environment in the UI-test Web form so the runner receives the production Base URL, while keeping running-job polling reliable with SQLite datetimes.

**Architecture:** Reuse the existing environment list API and the backend's existing `environment_id` field; only expose the missing selection in the React form. Normalize timestamps before duration subtraction in the UI-test service so polling cannot fail when SQLite returns naive datetimes.

**Tech Stack:** React, TypeScript, react-hook-form, Radix Select, Vitest, FastAPI, SQLAlchemy, pytest.

---

### Task 1: Cover the environment selector in the UI-test page

**Files:**
- Modify: `test-platform-v2/frontend/src/pages/uitest/index.tsx`
- Test: `test-platform-v2/frontend/src/pages/uitest/__tests__/UiRunDetail.test.tsx`

- [ ] **Step 1: Write the failing UI test**

Mock the environment API with `[{ id: 1, name: 'CamelTv 体育生产环境', base_url: 'https://www.camel1.tv' }]`, open the edit dialog for a job whose `environment_id` is `1`, and assert the select displays `CamelTv 体育生产环境`.

- [ ] **Step 2: Run the focused test and confirm it fails**

Run: `npm test -- src/pages/uitest/__tests__/UiRunDetail.test.tsx --run`

Expected: the environment label is absent because the form currently has no environment control.

- [ ] **Step 3: Implement the minimal form change**

Add `environment_id` to `uiJobFormSchema`, load environments with `fetchEnvironments`, reset it in create/edit flows, and render a `Select` whose values are `__none__` or the numeric environment id as a string. Convert the value back to `number | null` before calling `createUiJob`/`updateUiJob`.

- [ ] **Step 4: Run the focused test and type-check**

Run: `npm test -- src/pages/uitest/__tests__/UiRunDetail.test.tsx --run`

Run: `npm run build`

Expected: test and TypeScript build pass.

### Task 2: Make running-job duration calculation timezone-safe

**Files:**
- Modify: `test-platform-v2/backend/app/services/ui_test_service.py`
- Test: `test-platform-v2/backend/tests/test_ui_test_service.py`

- [ ] **Step 1: Write the failing service test**

Create a running `UiTestRun` whose `started_at` is naive, call `_run_to_dict`, and assert `duration` is a non-negative number instead of raising `TypeError`.

- [ ] **Step 2: Run the focused test and confirm it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_ui_test_service.py -q`

Expected: failure with `can't subtract offset-naive and offset-aware datetimes`.

- [ ] **Step 3: Normalize timestamps before subtraction**

Add a small helper that treats naive database timestamps as UTC and converts aware timestamps to UTC. Use it for both finished and running duration branches.

- [ ] **Step 4: Run the focused backend test**

Run: `.venv/Scripts/python.exe -m pytest tests/test_ui_test_service.py -q`

Expected: all focused tests pass.

### Task 3: Verify the normal-user Web flow

**Files:**
- No source files; verification only.

- [ ] **Step 1: Edit the existing DEV smoke task through `/uitest`**

Select `CamelTv 体育生产环境`, keep `specs/production-smoke.spec.ts`, and save.

- [ ] **Step 2: Trigger the task from the Web UI**

Expected: the new run detail shows Base URL `https://www.camel1.tv` instead of `-`.

- [ ] **Step 3: Record the outcome**

Expected: the runner reports non-zero test totals or a concrete product assertion failure, and the Web UI continues polling without a timezone exception.
