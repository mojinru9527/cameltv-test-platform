# QA Report — ExecutionRun canonical migration (PR-01)

## Verdict
PASS for PR-01 implementation slice.

## Scope verified
- Campaign/CampaignItem model + migration.
- `POST /api/v1/execution/campaigns/{campaign_id}/runs`.
- Campaign service delegates to existing `aitde.execution.service.create_run`.
- No second execution model or queue introduced.

## Commands and results
| Check | Result |
|---|---|
| `pytest tests -q` | 2681 passed, 51 skipped, 1 xfailed, 1 expected route-baseline failure before fixture update |
| `pytest tests/test_route_inventory.py -q` after baseline update | 1 passed |
| `pytest tests/test_campaign_execution.py tests/test_route_inventory.py tests/test_route_layer_orm_ban.py -q` | 8 passed |
| `pytest test-platform-v2/tests/test_execution_architecture_guard.py -q` | 3 passed |
| `ruff check app/ --select F821` | passed |
| `python scripts/ci/quality_ratchet.py` | PASS; ruff 768/768, mypy 193/193 |
| `dev-gate.ps1 -SkipFrontend` | PASS_WITH_WARN; HARD=0; existing WARN=330 |
| Alembic head | single head `20260918_execution_campaign` |
| SQLite upgrade head + inspect + downgrade | passed |

## Defects found and fixed
1. Implementation-pack sample used `CurrentUser.user_id`; actual contract is `current.user.id`. Fixed and covered by API test.
2. Sample code added Ruff findings (F401/E701/E702). Reformatted/fixed; quality ratchet remains at baseline.
3. New route intentionally changed route inventory; fixture updated to 654 routes and guard passes.

## Residual risk
- PR-01 does not yet link CampaignItem rows to ExecutionRun rows with a dedicated FK. The existing service contract and package sequence defer API/Plan cutover to PR-02+; no double-write was introduced.
- Frontend checks were skipped because this slice changes backend only; CI scope classification must confirm backend domain.
