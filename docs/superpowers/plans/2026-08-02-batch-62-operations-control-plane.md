# Batch 62 Operations Control Plane Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Build a standalone fail-closed release-control core that gives future CamelTv operations API/UI immutable release identity and trustworthy deployment facts.

**Architecture:** deploy/release-control contains Pydantic contracts, canonical hashes, SQLite persistence and a state-machine service. It cannot execute a target-environment deployment in this batch: test commands create only local persisted transitions, while production returns PRODUCTION_NOT_CONFIGURED before mutation.

**Tech Stack:** Python 3.12, Pydantic v2, sqlite3, hashlib, JSON, pytest and JSON Schema.

---

## File structure

| Path | Responsibility |
| --- | --- |
| deploy/release-control/src/cameltv_release/contracts.py | models, validation, canonical hash |
| deploy/release-control/src/cameltv_release/store.py | SQLite releases, locks, replay records and events |
| deploy/release-control/src/cameltv_release/state_machine.py | legal transitions and command results |
| deploy/release-control/src/cameltv_release/cli.py | schema consistency check |
| deploy/release-control/tests | executable contract and safety evidence |

### Task 1: Package and immutable manifest contract

**Files:** Create deploy/release-control/pyproject.toml, src/cameltv_release/__init__.py, src/cameltv_release/contracts.py, tests/test_contracts.py, examples/release-manifest.example.json.

- [ ] Write failing tests for stable hash and inline-secret rejection.
- [ ] Run python -m pytest deploy/release-control/tests/test_contracts.py -q; expect import failure.
- [ ] Implement models for release identity, artifacts, database target, Secret references and QA evidence.
- [ ] Canonicalize model JSON using sorted keys and compact separators; calculate SHA-256 from UTF-8 bytes.
- [ ] Reject mutable tags, invalid digest shape, multiple heads, target/head mismatch, missing evidence and secret-like fields.
- [ ] Re-run python -m pytest deploy/release-control/tests/test_contracts.py -q; expect PASS.

### Task 2: Schema exports

**Files:** Create schemas/release-manifest.v1.schema.json, schemas/environment.v1.schema.json, src/cameltv_release/cli.py, tests/test_schema_check.py.

- [ ] Write a failing schema-drift test that compares generated model schema to checked-in JSON.
- [ ] Run python -m pytest deploy/release-control/tests/test_schema_check.py -q; expect failure.
- [ ] Generate deterministic schemas and implement schema-check returning nonzero on drift.
- [ ] Run python -m pytest deploy/release-control/tests/test_schema_check.py -q and python -m cameltv_release.cli schema-check; expect exit code 0.

### Task 3: Store, replay and tamper-evident event chain

**Files:** Create src/cameltv_release/store.py, tests/test_store.py, tests/test_event_hash_chain.py.

- [ ] Write failing tests for new deployment, same-key replay, competing lock and edited event chain.
- [ ] Run python -m pytest deploy/release-control/tests/test_store.py deploy/release-control/tests/test_event_hash_chain.py -q; expect import failure.
- [ ] Implement SQLite with BEGIN IMMEDIATE, unique environment/idempotency tuple, explicit lock rows and hash-linked events.
- [ ] Verify every event hash includes sequence, predecessor hash and the complete non-secret event payload.
- [ ] Re-run the store tests; expect PASS.

### Task 4: Fail-closed state machine

**Files:** Create src/cameltv_release/state_machine.py, tests/test_state_machine.py, tests/test_idempotency_and_locking.py.

- [ ] Write failing tests for legal test transition, replay, held lock and zero persistence for production.
- [ ] Run python -m pytest deploy/release-control/tests/test_state_machine.py deploy/release-control/tests/test_idempotency_and_locking.py -q; expect import failure.
- [ ] Implement DRAFT to VALIDATED to TEST_DEPLOYING to TEST_VERIFYING to TEST_VERIFIED plus TEST_FAILED and rollback terminals.
- [ ] Reject production with PRODUCTION_NOT_CONFIGURED before validation-side persistence, lock creation or event writing.
- [ ] Re-run python -m pytest deploy/release-control/tests -q; expect PASS.

### Task 5: Core QA and consumer checkpoint

**Files:** Create deploy/release-control/README.md; later modify ADR-0015 and add API/UI only after core review.

- [ ] Run python -m pytest deploy/release-control/tests -q, python -m cameltv_release.cli schema-check and git diff --check.
- [ ] Document only tested core capability; retain adapters, API/UI and external deployment exercise as pending or blocked.
- [ ] Before FastAPI/React work, define tests for RBAC, Idempotency-Key, production rejection, ordered events, loading/error/empty UI states and one request per active view.

## Self-review

Tasks 1-4 cover immutable identity, schema consistency, durable state, audit integrity, locks, replay and fail-closed production behavior. No task assumes a real credential, environment, registry or deployment authority. The named models and stable codes are introduced before later consumers rely on them.
