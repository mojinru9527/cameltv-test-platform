# Batch 62 Operations Control Plane - Design Spec

> Design | 2026-08-02 | Ready for Slice 1

## Boundary

deploy/release-control is a standalone Python domain package. It owns immutable release identity, deployment state, locks, idempotency and audit facts. It does not import FastAPI application models, React, Docker, Jenkins, target databases or Secret Provider SDKs. The later operations API/UI are consumers.

    manifest -> canonical SHA-256 -> release store
                                    -> test command facade -> deployment/event facts
    future API/UI -----------------> read models and command results
    production command -----------> PRODUCTION_NOT_CONFIGURED

## Contract

A manifest contains release ID, 40-character Git SHA, frontend/backend image names and sha256 digests, SBOM evidence, exactly one Alembic head matching target revision, configuration schema, versioned environment-scoped Secret references and QA evidence. Sorted compact UTF-8 JSON is SHA-256 hashed.

Secret references use secret://environment/name@version. Values on secret-like keys including password, token, private_key, database_url and secret_key are rejected without echoing a value in errors.

## Outcomes

| Result | Code | Persistence |
| --- | --- | --- |
| New valid test request | ACCEPTED | one deployment and event |
| Replay | IDEMPOTENT_REPLAY | none |
| Concurrent environment | ENVIRONMENT_LOCKED | none |
| Illegal state | INVALID_TRANSITION | none |
| Production request | PRODUCTION_NOT_CONFIGURED | none |
| Invalid manifest | MANIFEST_INVALID | none |

An event includes sequence, release/deployment/environment IDs, actor, phase, from/to state, sanitized reason/evidence, predecessor hash and current hash. A sequence gap or digest mismatch fails verification.

## UI-forward constraints

Future UI must display a non-secret code plus text, source every timeline from ordered events, retain server-side production rejection even when controls are disabled, and make no mock release fact available as a production-looking record. UI implementation will use the repository UI convention skill before it begins.

## Security invariants

1. Production rejects before lock or deployment mutation.
2. Registered manifest content cannot change; changed content is a new release.
3. No automatic Alembic downgrade exists.
4. State storage path is executor configuration, never a hard-coded workspace path.
5. Slices 1-3 do not include side-effecting adapters.
