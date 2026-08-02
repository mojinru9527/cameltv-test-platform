# Dev Kanban - Batch 62 Operations Control Plane

## Project information

| Field | Value |
| --- | --- |
| Branch | feature/batch-62-operations-control-plane |
| Base | origin/main at 14b20c5 |
| Worktree | F:/CamelTv-worktrees/codex-batch-62-operations-control-plane |
| Workflow / executor | agent-team / codex |
| Ports | frontend 5199; backend 8029 |
| Created | 2026-08-02 |

| # | Slice | Plan | Code | Self-test | Review | Merge | Notes |
| --- | --- | :---: | :---: | :---: | :---: | :---: | --- |
| 1 | Immutable manifest contract | completed | completed | completed | pending | pending | 7 contract/schema tests green |
| 2 | Store, locks, idempotency, events | completed | completed | completed | pending | pending | hash-chain and conflict tests green |
| 3 | Test-only command facade | completed | completed | completed | pending | pending | 17 core tests green; production rejects |
| 4 | Adapter contract | completed | completed | completed | pending | pending | 5 adapter tests green; no external executor |
| 5 | Operations API/UI consumer | completed | completed | completed | pending | pending | global RBAC read-only consumer; production/executor UI omitted |
| 6 | Real test exercise | blocked | blocked | blocked | blocked | blocked | external owner needed |

## Current position

    Batch 62 -> Slice 5 -> local QA complete
    completed: Batch 61 W2 PR 90 merged into main
    completed: isolated worktree, executor confirmation, Product/PM/Design artifacts
    completed: immutable manifest, schema check, SQLite audit chain, lock/replay and state machine
    completed: immutable adapter inputs; test-only Jenkins contract rejects unconfigured execution
    completed: global RBAC read-only API consumes executor-owned SQLite facts; UI renders persisted release/event facts and production deferred notice
    next: update QA/Leader artifacts, commit Slice 5, mandatory push-range confirmation
    safety: no Test5, production, credentials, registry, Jenkins, Docker or migrations

## Blockers

| Blocker | Severity | Owner | Unblock condition |
| --- | --- | --- | --- |
| Real test release infrastructure | P0 | UNASSIGNED DevOps owner | registry, Runner, PostgreSQL, backup, Secret references, window |
| Old PostgreSQL snapshot | P0 | UNASSIGNED DBA/data owner | sanitized snapshot and migration assertions |
| Production readiness | P0 | UNASSIGNED release owner | registered infra, restore evidence, authorization |
| Backend ecdsa finding | P1 | UNASSIGNED security owner | remove/replace or expiring written acceptance |
