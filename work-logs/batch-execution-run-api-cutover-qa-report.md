# QA Report — ExecutionRun API cutover (PR-02)

## Verdict
PASS for PR-02 implementation slice.

## Changed behavior
- POST `/api/v1/apitest/tasks` now creates canonical Campaign + CampaignItems and invokes `start_campaign()`.
- New API task writes do not create `ApiExecutionTask` / `ApiExecutionTaskItem` and do not wake `api_task_worker`.
- Unmapped API cases fail with 409 before any Campaign/Run/legacy write.
- Historical task list/detail/cancel/retry endpoints remain available.

## Evidence
| Check | Result |
|---|---|
| `pytest tests -q` | 2685 passed, 51 skipped, 1 xfailed |
| API/campaign/isolation targeted tests | 55 passed |
| production guard tests | 23 passed |
| architecture guard | 4 passed |
| `ruff check app/ --select F821` | passed |
| quality ratchet | PASS; ruff 767/768, mypy 193/193 |
| `dev-gate.ps1 -SkipFrontend` | PASS_WITH_WARN; HARD=0, existing WARN=330 |
| SQLite Alembic upgrade/inspect/downgrade | passed |
| direct `app.main` import | passed |

## Risk
- Existing API cases without a canonical ScenarioAdapter or verified LegacyObjectMapping now receive 409. This is intentional cutover protection; migration must precede batch execution.
- Frontend was not changed in this slice; backend CI scope must classify the PR as backend.
