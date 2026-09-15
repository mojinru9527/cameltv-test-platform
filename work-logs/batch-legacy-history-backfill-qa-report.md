# QA Report — Legacy history backfill

> Batch: `legacy-history-backfill` | Date: 2026-09-16 | Executor: Codex

## Verdict

**PASS** for the scoped migration. Historical API and UI execution records are now fully linked to canonical `ExecutionRun` rows through the existing `legacy_bridge`.

## Results

| Check | Result |
|---|---|
| `python -m pytest tests/test_backfill_legacy_execution_links.py tests/test_legacy_delete_gate.py -q` | ✅ 5 passed |
| `python -m ruff check scripts/backfill_legacy_execution_links.py tests/test_backfill_legacy_execution_links.py --select F821` | ✅ passed |
| `python -m pytest -q` | ✅ 2691 passed, 51 skipped, 1 xfailed, 3 pre-existing failures |
| Full-scale preflight on restored production dump | ✅ 1942 API links created, 0 failures, fingerprint unchanged |
| Production API backfill | ✅ 1942 created, 0 failures |
| Production UI backfill | ✅ 130 created, 0 failures |
| Post-apply dry-run | ✅ API selected=0, UI selected=0 |

The 3 full-regression failures are the same `test_session_credentials.py` failures reproduced on clean main `fede5118`:
`test_configured_fetch_returns_token_and_key`, `test_form_encoded_credentials_fetch`, `test_execute_with_session_injection`.

## Production evidence

- API link coverage: **1999/1999**
- UI link coverage: **203/203**
- `LegacyExecutionLink` total: **2202**
- `ExecutionRun` total: **2206** (2072 `LEGACY_BRIDGE` + 134 prior)
- Legacy fingerprints unchanged:
  - `api_execution_task`: `067ceb6512b89413534285236dc34a99`
  - `api_execution_task_item`: `ed83be4f9a783df33fe872af91c0109c`
  - `plan_execution_job`: `EMPTY`

## Restore drill

- Latest release-console backup: `/opt/cameltv-backup/cameltv-prod-20260915-160754.dump`
- SHA256: `8ae833df56a0fc08f25673e812437ff4b61c826a24c514300ad7b3df6c4b7f5e`
- Restored into isolated temporary PostgreSQL 16; `pg_restore --exit-on-error` passed; key counts verified; temporary container removed.
- Gate flags updated: `historical_mapping_complete=true`, `rollback_restore_drill_success=true`.

## CI classification

Changed paths are backend scripts/tests plus work-logs, so backend required regression must run; frontend may be skipped by the classifier and no frontend behavior changed.

## Residual risk

- `legacy_urls_readonly_or_redirect` remains false until the release containing PR #451 is deployed to production.
- The zero-write observation remains active until `2026-09-22T13:37:06Z`.
- Product/QA/Architecture sign-off remains pending.
