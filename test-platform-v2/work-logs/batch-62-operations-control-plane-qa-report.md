# Batch 62 Operations Control Plane - QA Report

> QA | 2026-08-02 | Scope: release-control core plus Slice 5 read-only API/UI | Verdict: PASS FOR LOCAL CORE AND READ-ONLY CONSUMER

## Scope and safety boundary

This report covers the standalone deploy/release-control domain core and the read-only test-platform consumer. The API reads the executor-owned SQLite fact store through an explicit configured path; it does not write to the application database or fabricate deployment facts. The UI only renders these persisted records and ordered events. This does not claim a real test deployment, database migration, rollback exercise, Jenkins/Runner adapter, Test5 validation or production readiness. No external host, VPN, credential, registry, Docker, Jenkins, PostgreSQL or production command was contacted.

## Executed evidence

| Command | Exit | Result |
| --- | ---: | --- |
| python -m pytest deploy/release-control/tests -q | 0 | 22 passed |
| python -m cameltv_release.cli schema-check | 0 | checked-in schema equals Pydantic model |
| pytest test-platform-v2/backend/tests -q | 0 | 980 passed, 3 skipped |
| ruff check test-platform-v2/backend/app --select F821 | 0 | passed |
| npm run typecheck | 0 | passed |
| npm run build | 0 | passed |
| npm test -- --run | 0 | 77 files, 293 tests passed |
| pytest test-platform-v2/backend/tests/test_ops_release_api.py -q | 0 | 3 passed: global RBAC, persisted facts/event order, unconfigured 503 |
| npm test -- --run src/pages/operations-release/index.test.tsx | 0 | 2 passed: deferred production state and one event request after selection |
| git diff --check | 0 | no whitespace errors |

Tests cover canonical manifest identity, malformed/mutable/secret-bearing manifest rejection, unique Alembic target, idempotent replay, lock exclusion, release-ID immutability, hash-chain tamper detection, legal test-only transitions, terminal lock release, production zero-persistence rejection and sanitized deployment export. Adapter tests prove Compose images bind to manifest digests with no build or mutable tag, while Jenkins accepts only release identity, test and idempotency then fails closed because no external executor is configured.

## Residual risks and blockers

| ID | Level | Status | Next action |
| --- | --- | --- | --- |
| OPS2-CORE-001 | P1 | Partial | Immutable Compose/Jenkins contracts pass locally; a real executor is intentionally absent and returns EXTERNAL_EXECUTOR_NOT_CONFIGURED. |
| OPS2-CORE-002 | P1 | Partial | Slice 5 provides global-RBAC read-only API/UI backed exclusively by store records. Write commands, approvals, environment dashboard and real executor remain deliberately absent. |
| B60-BLK-005 / OPS1 | P0 | External BLOCKED | Named DevOps/DBA owner must provide registry, Runner, PG16, backup and Secret-reference mechanism. |
| B61-P1-001 | P1 | FAIL, out of scope | Resolve or formally accept the backend ecdsa advisory. |

## Conclusion

The core and its read-only consumer are suitable for controlled inspection of persisted release facts. It is not evidence that a test or production release is ready. Production remains DEFERRED; only its stable fail-closed response was verified.
