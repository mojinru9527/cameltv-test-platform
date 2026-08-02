# Batch 62 Operations Control Plane - PM Plan

> PM | 2026-08-02 | In progress

| Slice | Deliverable | Acceptance | Boundary |
| --- | --- | --- | --- |
| 1 | Contracts | Valid manifests hash canonically; invalid inputs reject | no executor |
| 2 | Durable state | SQLite store, locks, idempotency, hash-chain events | no deployment |
| 3 | Command facade | Test dry-run transitions and production reject | no Docker/Jenkins |
| 4 | Adapters | Compose/Jenkins input contracts | after core review |
| 5 | API/UI | RBAC consumer backed by real records | separate UI slice |
| 6 | Exercise | real test release and rollback | externally blocked |

## Slice 1 tasks

1. Write failing tests for valid manifests, mutable tags, malformed digest, inline secret, missing evidence and multiple heads.
2. Implement Pydantic models, canonical JSON and SHA-256 hash.
3. Export checked-in JSON schemas with a CLI schema consistency check.
4. Include non-secret manifest and environment fixtures.

## Slice 2 tasks

1. Write failing tests for the state graph, replay, competing environment locks and event tampering.
2. Implement SQLite releases, deployments, locks, idempotency records and append-only events.
3. Implement legal test transitions and release locks only after validation.
4. Reject production before persistence.

## Slice 3 tasks

1. Add data-only dry-run and failure-injection tests.
2. Export sanitized JSON and Markdown facts.
3. Run the complete release-control suite and schema check.

## Required checks

- python -m pytest deploy/release-control/tests -q
- python -m cameltv_release.cli schema-check
- git diff --check

## Risks

| Risk | Control |
| --- | --- |
| Prototype appears to deploy | no runner dependency; tests assert zero adapter calls |
| Secrets leak | only secret references validate; exports are tested |
| UI outruns domain | API/UI begins only after core tests pass |
