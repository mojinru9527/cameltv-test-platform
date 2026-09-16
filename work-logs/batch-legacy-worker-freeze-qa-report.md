# QA Report — Legacy worker freeze

> Batch: `legacy-worker-freeze` | Date: 2026-09-16 | Result: **PASS**

## Scope verified

- `app.worker.task_consumers` no longer imports or starts `api_task_worker` or `plan_execution_queue`.
- Worker health no longer requires the frozen loops.
- `api_task_worker.py`, `plan_execution_queue.py`, historical models, read-only `list_jobs` and Legacy tables remain present.
- Delete gate remains false for zero-write and signoff; no deletion occurred.

## Checks

| Check | Result |
|---|---|
| `python -m pytest tests/resource_budget/test_worker_ownership.py tests/test_api_task_worker.py tests/test_legacy_delete_gate.py -q` | ✅ 25 passed |
| `python -m pytest tests/test_execution_architecture_guard.py -q` | ✅ 11 passed |
| `python -m ruff check app/worker.py --select F821` | ✅ passed |
| `python -m pytest -q` | ✅ 2691 passed, 51 skipped, 1 xfailed, 3 pre-existing failures |

The same three `test_session_credentials.py` failures reproduce on the clean main baseline. No new failure was introduced.

## Production impact

This batch is not deployed in this step. Production remains on `release-20260916-0002`, and the zero-write observation continues unchanged. The worker freeze becomes effective with the next release train.

## Residual risk

- Historical pending Legacy work will no longer be processed automatically after the freeze is deployed; this is intentional because Legacy writes are closed and history remains readable.
- File/table deletion is still gated by PR-09 and is not part of this batch.
