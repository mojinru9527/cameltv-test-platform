# Batch 62 Operations Control Plane - QA Report

> QA | 2026-08-02 | Scope: release-control core Slices 1-4 | Verdict: PASS FOR LOCAL CORE ONLY

## Scope and safety boundary

This report covers only the standalone deploy/release-control domain core. It does not claim a real test deployment, database migration, rollback exercise, Jenkins/Runner adapter, operations API/UI, Test5 validation or production readiness. No external host, VPN, credential, registry, Docker, Jenkins, PostgreSQL or production command was contacted.

## Executed evidence

| Command | Exit | Result |
| --- | ---: | --- |
| python -m pytest deploy/release-control/tests -q | 0 | 22 passed |
| python -m cameltv_release.cli schema-check | 0 | checked-in schema equals Pydantic model |
| git diff --check | 0 | no whitespace errors |

Tests cover canonical manifest identity, malformed/mutable/secret-bearing manifest rejection, unique Alembic target, idempotent replay, lock exclusion, release-ID immutability, hash-chain tamper detection, legal test-only transitions, terminal lock release, production zero-persistence rejection and sanitized deployment export. Adapter tests prove Compose images bind to manifest digests with no build or mutable tag, while Jenkins accepts only release identity, test and idempotency then fails closed because no external executor is configured.

## Residual risks and blockers

| ID | Level | Status | Next action |
| --- | --- | --- | --- |
| OPS2-CORE-001 | P1 | Partial | Immutable Compose/Jenkins contracts pass locally; a real executor is intentionally absent and returns EXTERNAL_EXECUTOR_NOT_CONFIGURED. |
| OPS2-CORE-002 | P1 | Pending | Add RBAC API/UI consumers backed exclusively by store records. |
| B60-BLK-005 / OPS1 | P0 | External BLOCKED | Named DevOps/DBA owner must provide registry, Runner, PG16, backup and Secret-reference mechanism. |
| B61-P1-001 | P1 | FAIL, out of scope | Resolve or formally accept the backend ecdsa advisory. |

## Conclusion

The core is suitable as the factual source for future adapter/API/UI slices. It is not evidence that a test or production release is ready. Production remains DEFERRED; only its stable fail-closed response was verified.
