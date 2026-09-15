# Legacy history backfill + restore drill evidence

> Date: 2026-09-16 | Production release: `release-20260915-0003`

## Historical mapping

Before:

| Object | Linked | Total |
|---|---:|---:|
| `API_TASK_ITEM` | 57 | 1999 |
| `UI_RUN` | 73 | 203 |

Applied through the existing `legacy_bridge` with `run_id=None`:

- API items created: **1942**, failures: **0**
- UI runs created: **130**, failures: **0**
- Final `LegacyExecutionLink`: **2202**
- Final canonical `ExecutionRun`: **2206**
- Post-apply dry-run: `selected_items=0`, `selected_ui_runs=0`

Legacy fingerprints were unchanged before/after:

| Table | Rows | Fingerprint |
|---|---:|---|
| `api_execution_task` | 37 | `067ceb6512b89413534285236dc34a99` |
| `api_execution_task_item` | 1999 | `ed83be4f9a783df33fe872af91c0109c` |
| `plan_execution_job` | 0 | `EMPTY` |

## Restore drill

- Backup: `/opt/cameltv-backup/cameltv-prod-20260915-160754.dump`
- SHA256: `8ae833df56a0fc08f25673e812437ff4b61c826a24c514300ad7b3df6c4b7f5e`
- Size: 62 MiB
- Restored into an isolated temporary PostgreSQL 16 container with `pg_restore --exit-on-error --no-owner --no-privileges`
- Verified counts: `alembic_version=1`, `api_execution_task=37`, `api_execution_task_item=1999`, `execution_runs=134`, `legacy_execution_links=130`, `test_scenarios=4`
- Temporary restore container removed after verification

## Gate changes

- `historical_mapping_complete`: `false` → `true`
- `rollback_restore_drill_success`: `false` → `true`
- `legacy_new_writes_zero_full_cycle` remains blocked by the active production observation.
- `legacy_urls_readonly_or_redirect` remains false until the release containing PR #451 is deployed to production.
- Product/QA/Architecture sign-off remains pending.
