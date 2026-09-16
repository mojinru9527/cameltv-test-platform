# PM Plan — Legacy delete final (PR-09)

## Tasks

| # | Task | Files | Acceptance |
|---|---|---|---|
| 1 | Remove Legacy API executor | `backend/app/services/api_task_worker.py` | File absent; no imports remain in app/scripts. |
| 2 | Remove Legacy plan executor | `backend/app/services/plan_execution_queue.py` | File absent; read-only history service remains. |
| 3 | Remove Legacy write helpers | `api_execution_service.py`, `runner_execution_service.py` | Old create/claim/report helpers absent. |
| 4 | Close implicit bridge creation | `legacy_bridge.py`, `playwright_executor.py`, `temporal/activities.py` | Bridge requires explicit `run_id`; no auto LEGACY_BRIDGE run. |
| 5 | Preserve read-only history | `plan_execution_history.py`, API route | Historical jobs readable without ORM access in route. |
| 6 | Update guards and tests | backend tests, `tests/test_execution_architecture_guard.py` | Deleted files and absent writers guarded. |

## Evidence

- `ruff check app/ --select F821`
- focused backend tests
- backend regression with the known `test_session_credentials` baseline
- architecture guard
- post-merge production health/login/read-only verification
