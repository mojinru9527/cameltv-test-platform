# QA Report — Plan/CI cutover (PR-03)

## Verdict
PASS for the implemented PR-03 slice.

## Evidence
| Check | Result |
|---|---|
| targeted plan/API/campaign regression | 43 passed |
| async plan tests | 5 passed |
| batch148 production/precheck tests | 8 passed |
| architecture guard | 6 passed |
| ruff F821 | passed |
| quality ratchet | PASS; ruff 767/768, mypy 193/193 |
| CI legacy-executor scan | passed; no workflow references old executors |

## Behavior
- execute-all calls `create_plan_campaign()` and returns campaign_id/run_ids.
- async_mode no longer creates PlanExecutionJob.
- environment/base_url/token prechecks remain.
- production guard requires explicit confirm_prod for canonical plan execution.
- unmapped API cases fail closed.
