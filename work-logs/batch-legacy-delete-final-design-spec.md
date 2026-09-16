# Design Spec — canonical ExecutionRun deletion boundary

Canonical chain:

```text
Campaign -> ExecutionRun -> ExecutionStep -> AssertionResult / EvidenceArtifact
```

## Deleted execution paths

- API bulk task daemon loop.
- Plan dispatch executor, heartbeat and worker loop.
- Legacy Temporal runner activities.
- Legacy runner write helpers.
- Implicit `LEGACY_BRIDGE` Run creation.

## Preserved read surfaces

- `ApiExecutionTask` / `ApiExecutionTaskItem` ORM models and project-scoped
  read queries.
- `PlanExecutionJob` ORM model and `GET /execution-jobs` historical read.
- `LegacyExecutionLink` mappings and historical bridge migration.

## Bridge contract

`bridge_api_item` and `bridge_ui_run` require an existing canonical `run_id`.
If it is absent, they return `410`; they never create a run with empty scenario
bindings. The historical backfill command creates the LEGACY_BRIDGE run
explicitly through the canonical repository and then passes that id to the
bridge.
