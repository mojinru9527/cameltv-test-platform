# Batch PRD — Legacy execution readonly endpoints

mode: full
executor: codex
date: 2026-09-15

## Problem

Canonical campaign cutover is complete for API batch and plan execution creation, but several historical execution URLs remain writable:

- `POST /api/v1/apitest/tasks/{task_id}/cancel`
- `POST /api/v1/apitest/tasks/{task_id}/retry-failed`
- `DELETE /api/v1/apitest/tasks/{task_id}`
- `POST /api/v1/apitest/runner/tasks|claim|report`

These routes can still mutate `ApiExecutionTask`, `ApiExecutionTaskItem`, or `RunnerExecutionTask`, which violates the Legacy readonly gate and can invalidate the production zero-write observation.

## Goal

Make all Legacy execution mutation URLs read-only without deleting historical data or introducing another execution model. Historical reads remain available. New execution must use canonical Campaign → ExecutionRun.

## Requirements

1. Legacy task cancel/retry/delete return HTTP `410 Gone` for the owning project and do not write legacy rows or change task state.
2. Legacy runner task create/claim/report return HTTP `410 Gone` and do not mutate runner task state.
3. Existing legacy GET/list/detail/curl/analysis endpoints stay read-only and project-scoped.
4. Frontend historical task view removes cancel/retry/delete actions and explains that execution must use the canonical execution center.
5. Tests prove both HTTP behavior and zero legacy mutation.
6. No legacy table/code deletion, no schema change, no new execution system.

## Acceptance

- Focused backend tests pass and assert row counts/state are unchanged on `410`.
- Architecture guard prevents reintroduction of writes in legacy mutation route blocks.
- Frontend typecheck/build and affected Vitest pass.
- Production observation remains zero-write after deploy.
