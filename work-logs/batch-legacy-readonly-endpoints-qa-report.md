# QA Report — Legacy readonly endpoints

> Batch: `legacy-readonly-endpoints` | Date: 2026-09-15 | Executor: Codex

## Verdict

**PASS** for the scoped behavior. No new backend failures were introduced.

## Changed behavior verified

- `POST /api/v1/apitest/tasks/{id}/cancel` → `410`, no state change.
- `POST /api/v1/apitest/tasks/{id}/retry-failed` → `410`, no new legacy task/item.
- `DELETE /api/v1/apitest/tasks/{id}` → `410`, task/item count unchanged.
- `POST /api/v1/apitest/runner/tasks|claim|report` → `410`, runner task count unchanged.
- Foreign-project historical objects remain `404`.
- Historical GET/list/detail/curl/analysis stay available.
- Frontend historical task view has no cancel/retry/delete controls and links to `/executions`.

## Commands and results

| Command | Result |
|---|---|
| `python -m pytest tests/test_api_task_worker.py tests/test_batch206_runner.py tests/test_apitest_project_isolation.py -q` | ✅ 48 passed |
| `python -m pytest tests/test_execution_architecture_guard.py -q` | ✅ 10 passed |
| `python -m ruff check app/api/v1/apitest_tasks.py app/api/v1/api_runner.py --select F821` | ✅ passed |
| `npm run typecheck` | ✅ passed |
| `npm run lint` | ✅ passed |
| `npm test` | ✅ 164 files, 710 tests passed |
| `npm run build` | ✅ passed |
| `pwsh scripts/git/dev-gate.ps1 -RepositoryPath (Get-Location).Path` | ✅ `PASS_WITH_WARN`, HARD=0, all hard gates/route guards passed |

## Full backend regression

`python -m pytest -q` result:

```text
2687 passed, 51 skipped, 1 xfailed, 3 failed in 639.37s
```

The same 3 failures reproduce unchanged on clean main `fede5118`:

```text
test_session_credentials.py::test_configured_fetch_returns_token_and_key
test_session_credentials.py::test_form_encoded_credentials_fetch
test_session_credentials.py::test_execute_with_session_injection
```

They are a pre-existing baseline failure set, not introduced by this batch.

## CI classification expectation

Changed files cover `test-platform-v2/backend/**` and `test-platform-v2/frontend/**`, so PR CI must run both backend and frontend required jobs. Neither domain may rely on skipped jobs as evidence.

## Residual risk

- Legacy service/worker code remains present by design until the observation and deletion gate pass.
- The routes are fail-closed before any DB mutation; future callers must use canonical `/api/v1/execution` runner contracts.
- No production deployment is required to validate the local gate; rollout remains subject to the normal release train.
