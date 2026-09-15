# Legacy readonly production evidence — release-20260916-0002

> Date: 2026-09-16 | Git SHA: `bfac06ca0082c97e6fffc623e6099ebcfb49c804` | State: `PRODUCTION_VERIFIED`

## Production deployment

- Release: `release-20260916-0002`
- Runtime: split topology
- Backend/frontend rebuilt from current main; runner/ai-gateway reused verified main images under the new release tag.
- All six production services healthy; health endpoint 200; `sportsadmin` login returns user_id=4.

## Legacy mutation URLs

Authenticated production probes returned `410 Gone` without changing state:

| Route | Status |
|---|---:|
| `POST /api/v1/apitest/tasks/1/cancel` | 410 |
| `POST /api/v1/apitest/tasks/1/retry-failed` | 410 |
| `DELETE /api/v1/apitest/tasks/1` | 410 |
| `POST /api/v1/apitest/runner/claim` | 410 |

## Historical mapping

- `API_TASK_ITEM`: 1999/1999 linked
- `UI_RUN`: 203/203 linked
- `LegacyExecutionLink`: 2202
- canonical `ExecutionRun`: 2206
- Post-apply dry-run: selected API=0, selected UI=0

Legacy fingerprints remain unchanged:

| Table | Rows | Fingerprint |
|---|---:|---|
| `api_execution_task` | 37 | `067ceb6512b89413534285236dc34a99` |
| `api_execution_task_item` | 1999 | `ed83be4f9a783df33fe872af91c0109c` |
| `plan_execution_job` | 0 | `EMPTY` |

## Restore drill

- Backup: `/opt/cameltv-backup/cameltv-prod-20260915-160754.dump`
- SHA256: `8ae833df56a0fc08f25673e812437ff4b61c826a24c514300ad7b3df6c4b7f5e`
- Restored into an isolated PostgreSQL 16 instance with `pg_restore --exit-on-error --no-owner --no-privileges`.
- Verified key counts and removed the temporary instance.

## Remaining PR-09 gate

- `legacy_new_writes_zero_full_cycle`: observation still active through `2026-09-22T13:37:06Z`.
- `product_qa_architecture_signoff`: still open.
