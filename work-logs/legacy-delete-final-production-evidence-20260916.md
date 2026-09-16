# Legacy delete final — production evidence

> Date: 2026-09-16 | PR: #455 | Git SHA: `72a3002d01b9bc45e004695d0d46368e0892200a`

## Deployment

- Release: `release-20260916-0003`
- Deployment id: `e3f4b92c95064e7db7230548c79b0c6e`
- State: `PRODUCTION_VERIFIED`
- Runtime: split topology
- Backup before deployment:
  `/opt/cameltv-backup/cameltv-prod-20260916-121859.dump`

Backend and runner images were built from the merged commit. Frontend and
ai-gateway content was unchanged from the previously verified release and was
retagged into the new immutable release tag. The runner image was built from
the verified `cameltv-tp-runner:main` base with the final `app/` source copied
in and the deleted executor files explicitly removed.

## Health and access

- External health: HTTP 200
- `sportsadmin` login: `user_id=4`
- All six production services: healthy

## Legacy fail-closed probes

| Route | Status |
|---|---:|
| `POST /api/v1/apitest/tasks/1/cancel` | 410 |
| `POST /api/v1/apitest/tasks/1/retry-failed` | 410 |
| `DELETE /api/v1/apitest/tasks/1` | 410 |
| `POST /api/v1/apitest/runner/claim` | 410 |

## Final code and worker check

The following images no longer contain
`/app/app/services/api_task_worker.py` or
`/app/app/services/plan_execution_queue.py`, and do contain
`plan_execution_history.py`:

- `cameltv-tp-backend:release-20260916-0003`
- `cameltv-tp-runner:release-20260916-0003`
- the `aitde-worker` container using the runner image

No Legacy worker loop names, import tracebacks or `ModuleNotFound` errors were
found in the new worker logs.

## Zero-write fingerprint

| Table | Rows | New | Updated | Fingerprint |
|---|---:|---:|---:|---|
| `api_execution_task` | 37 | 0 | 0 | `067ceb6512b89413534285236dc34a99` |
| `api_execution_task_item` | 1999 | 0 | 0 | `ed83be4f9a783df33fe872af91c0109c` |
| `plan_execution_job` | 0 | 0 | 0 | `EMPTY` |

The observation check returned `drift=false`. The user waived the long
single-tester observation period and supplied Product, QA and Architecture
signoffs; the PR-09 deletion gate is therefore fully green.
