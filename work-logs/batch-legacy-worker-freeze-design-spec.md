# Batch Design Spec — Legacy worker freeze

## Operational behavior

- Worker process starts: scheduler, AI tasks, DSH, knowledge agent queue and UI pool cleanup.
- Worker process does not start: API legacy task loop or plan execution queue loop.
- Health checks only depend on consumers that are intentionally started.
- `api_task_worker` / `plan_execution_queue` modules remain importable for historical/read-only tools and tests.

## Security and migration

- No new queue or execution system.
- Canonical ExecutionRun remains the only new execution owner.
- Legacy rows remain readable and mapped.
- Deletion remains governed by `legacy_delete_gate.json`.
