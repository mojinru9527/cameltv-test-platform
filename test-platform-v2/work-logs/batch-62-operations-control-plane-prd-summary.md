# Batch 62 Operations Control Plane - PRD Summary

> Product | 2026-08-02 | Approved for implementation

## Problem

Batch 61 W2 is already merged, but its planned release-control engine was never delivered. The repository has an operations architecture and a future UI/API design, but no durable, verifiable release fact source. A UI built first would expose mock or unbound deployment information.

Batch 62 first delivers the smallest authoritative core: immutable release identity, append-only evidence, legal test-release transitions, idempotency, environment locking, and a production path that rejects before side effects. Later API/UI work consumes this core rather than creating a second deployment model.

## Success measures

| Measure | Target | Evidence |
| --- | ---: | --- |
| Invalid or mutable manifests accepted | 0 | contract tests |
| Plaintext secrets persisted or exported | 0 | validation and export tests |
| Duplicate or illegal transitions accepted | 0 | state and idempotency tests |
| Production operation reported successful | 0 | rejecting command tests |
| Event tampering undetected | 0 | hash-chain tests |

## Scope

- New standalone deploy/release-control Python package, contracts, schemas, SQLite store and tests.
- Canonical manifest hashing; only versioned, environment-scoped Secret references are allowed.
- Test-only command/state semantics with no Docker, Jenkins, registry, database migration or network side effect.
- A stable read/command interface for later operations API/UI slices.

## Non-goals and boundaries

- No Test5/VPN access, production deployment, production migration, real registry, secret provider, SSH, Docker Compose or Jenkins invocation.
- No secret values, connection strings, tokens, private keys, or credentials in Git, fixtures, output, events or manifests.
- Existing product release-bundles are not deployment release-control records.
- B61-P1-001, Test5 prerequisites, old PostgreSQL snapshot, and cloud-account conditions remain open.
- B60-P1-010 OPS2 is addressed by establishing its required fact source. B60-P2-002 touch audit and B60-P2-006 knowledge-card density are separate UI work and remain deferred.

## User stories

### US-1 Immutable release identity

Given a valid non-production manifest, when it is canonicalized, then its SHA-256 identity is stable. Given a mutable tag, malformed digest, inline secret, missing QA evidence, or multiple Alembic heads, when registration is attempted, then validation rejects it without persistence.

### US-2 Truthful test workflow

Given a validated release and test environment, when a legal command has a new idempotency key, then exactly one deployment and append-only event sequence are recorded. When the key is replayed, then the first result is returned and no second transition is created.

### US-3 Fail-closed environment control

Given a held test lock, when another release requests the same environment, then it receives ENVIRONMENT_LOCKED. Given production, when any deployment command is requested, then it returns PRODUCTION_NOT_CONFIGURED and creates no success record.

### US-4 Tamper-evident timeline

Given persisted events, when an event payload, predecessor, sequence, or ordering is changed, then verification fails.

## External blockers

Real test deployment remains blocked pending a named DevOps owner, registry, Runner/Jenkins, PostgreSQL 16, backup destination, Secret-reference mechanism and authorized window. Production remains DEFERRED pending registered infrastructure, DNS/TLS, monitoring, restore evidence and a separately authorized window.
