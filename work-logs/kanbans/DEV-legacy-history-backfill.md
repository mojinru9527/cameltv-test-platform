# Dev Kanban — Legacy history backfill

> Batch: `legacy-history-backfill` | Mode: light | Executor: Codex

| Slice | Design | Code | Self-test | QA | Merge |
|---|---:|---:|---:|---:|---:|
| Read-only inventory / dry-run planner | ✅ | ✅ | ✅ | ✅ | ⏳ |
| Idempotent apply through `legacy_bridge` | ✅ | ✅ | ✅ | ✅ | ⏳ |
| Unit tests for dry-run/apply/idempotency/isolation | ✅ | ✅ | ✅ | ✅ | ⏳ |
| Production dry-run + apply evidence | ✅ | ✅ | ✅ | ✅ | ⏳ |

## Current position

Migration complete in production; pending commit/PR/merge and final observation gates.

