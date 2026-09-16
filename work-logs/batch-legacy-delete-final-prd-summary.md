# PRD — Legacy delete final (PR-09)

mode: full
executor: codex
date: 2026-09-16

## Problem

Canonical `ExecutionRun` cutover is complete, but the repository still carries
two executable Legacy queues (`api_task_worker`, `plan_execution_queue`) and
several Legacy write entry points. Keeping them leaves a second way to mutate
historical execution tables and contradicts the single canonical execution
model.

## Success metrics

- Canonical write paths remain `Campaign -> ExecutionRun -> Runner`.
- `api_task_worker.py` and `plan_execution_queue.py` are absent.
- Legacy task/job mutation APIs fail closed with `410` and cannot write rows.
- Legacy history remains readable through read-only services.
- Legacy bridge never creates an `ExecutionRun` implicitly; migration must pass
  a real canonical `run_id`.
- Architecture, project-isolation and rollback guards remain green.

## Non-goals

- Do not drop or physically delete historical tables in this batch.
- Do not add a new execution model, queue, or status machine.
- Do not remove read-only historical endpoints or mapping records.

## C-conditions check

No active C condition covers this deletion. The user waived the long
single-tester observation period on 2026-09-16 and supplied:

```text
Product signoff: 批准 Legacy 删除方案与最终范围
QA signoff: 批准现有验证证据与观察流程
Architecture signoff: 批准 canonical ExecutionRun 架构收口和 Legacy 删除
```

## Acceptance

Given a historical `ApiExecutionTask` or `PlanExecutionJob`
When a Legacy mutation endpoint or runner helper is called
Then it must fail closed or be absent, with no row change.

Given historical data that still needs mapping
When the migration command runs
Then it creates a real canonical `LEGACY_BRIDGE` run explicitly and links the
historical evidence to that `run_id`.
