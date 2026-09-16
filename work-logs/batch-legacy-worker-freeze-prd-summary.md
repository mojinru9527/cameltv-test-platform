# Batch PRD — Legacy worker freeze

mode: full
executor: codex
date: 2026-09-16

## Problem

Canonical cutover and Legacy URL readonly are complete, but the worker process still starts `api_task_worker` and `plan_execution_queue` execution loops. They can mutate historical `ApiExecutionTask` / `PlanExecutionJob` rows if stale pending data is claimed, adding risk to the zero-write observation.

## Goal

Stop starting the two Legacy execution loops in the worker process while preserving their files, historical tables and read-only plan job queries. This is a freeze, not deletion.

## Requirements

1. `app.worker.task_consumers` must not import or start `api_task_worker` or `plan_execution_queue`.
2. Worker health must not depend on the frozen loops.
3. `api_task_worker.py`, `plan_execution_queue.py`, historical models and `list_jobs` remain present.
4. Canonical Campaign/ExecutionRun and all non-Legacy worker consumers continue unchanged.
5. Delete gate remains false for zero-write/signoff; no table/file deletion.

## Acceptance

- Architecture guard asserts the worker entrypoint has no Legacy execution loop references.
- Worker ownership and API-task worker tests pass.
- Full backend regression has no new failure beyond known `session_credentials` baseline.
