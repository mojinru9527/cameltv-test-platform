# Batch PM Plan — Legacy worker freeze

| ID | Task | Output |
|---|---|---|
| T1 | Remove Legacy execution loops from worker startup | `backend/app/worker.py` |
| T2 | Add worker-entrypoint architecture guard | `tests/test_execution_architecture_guard.py` |
| T3 | Run focused worker/architecture/delete-gate tests | QA evidence |
| T4 | Record zero-write and rollback impact | QA/Leader work-logs |

## Out of scope

- Deleting files, tables, workers, bridge or historical models.
- Changing canonical ExecutionRun APIs.
- Modifying production during this local batch; deployment follows PR merge.

## Risk

The old loops are no longer started, so historical pending work will not be processed automatically. This is intentional: Legacy writes are frozen, and historical read APIs remain available.
