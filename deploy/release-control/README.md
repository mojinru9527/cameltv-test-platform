# CamelTv Release Control Core

deploy/release-control is the local, fail-closed domain core for the future CamelTv operations release platform. It records immutable release facts and test-deployment state; it does not contact a registry, Jenkins, Docker, a target host, PostgreSQL, a Secret Manager, Test5, or production.

## Implemented core

- Immutable release-manifest validation: digest-bound frontend/backend artifacts, SBOM/OpenAPI checksums, one Alembic head, QA evidence and versioned Secret references.
- Canonical JSON SHA-256 manifest identity and checked-in JSON Schema drift detection.
- Executor-owned SQLite state: release records, idempotency keys, one test-environment lock and append-only hash-linked events.
- Legal local transitions from DRAFT through TEST_VERIFIED, plus failure and rollback terminals with no infrastructure adapter.
- Fail-closed result codes: PRODUCTION_NOT_CONFIGURED, ENVIRONMENT_LOCKED, IDEMPOTENT_REPLAY, INVALID_TRANSITION, and RELEASE_ID_CONFLICT.
- Sanitized export that omits the manifest and every Secret reference.

## Deliberately excluded

- Real test/production deployment, Compose/Jenkins/Runner adapters, registry access, migrations, health probes, backup/restore and notifications.
- FastAPI operations endpoints and React operations views. Those later slices must consume these records rather than invent mock deployment facts.
- Any production request: non-test commands return PRODUCTION_NOT_CONFIGURED before creating a lock, deployment or event.

## Local verification

    $env:PYTHONPATH = (Join-Path (Get-Location) 'deploy/release-control/src')
    python -m pytest deploy/release-control/tests -q
    python -m cameltv_release.cli schema-check

The example manifest uses .invalid hostnames and fabricated digest values. It is a contract fixture, not a deployable release.

## Persistence boundary and next checkpoint

ReleaseStore receives an explicit SQLite path from its executor. That path belongs outside a Jenkins workspace and outside the test-platform application database. The repository supplies no default state location, credential or target address.

Before adapters or API/UI are added, retain the core test suite and add consumer contract tests. A real test exercise remains blocked until named DevOps/DBA owners provide a registry, Runner, PostgreSQL 16, backup destination, Secret-reference mechanism and an authorized window. Production remains deferred.
