# Batch 231 - PM Plan

> PM | Date: 2026-09-06 | Mode: full | Executor: Codex

## Delivery Slices

| Slice | Scope | Primary Tests | Dependency |
|---|---|---|---|
| S1 | Playwright and version-run anti-fake-success | executor + version-task service tests | none |
| S2 | Version-task project isolation and historical reconciliation | API contract + migration tests | S1 |
| S3 | Mission Gate evidence semantics | v35 gate wiring + acceptance UI | none |
| S4 | Scenario run contract and shared error normalization | execution API/client/page tests | none |
| S5 | AI/DSH/provider and Durable Worker readiness | service/API/UI readiness tests | S4 |
| S6 | Schedule duplicate trigger semantics | schedule page tests | none |
| S7 | SMART FULL fallback, source refs, review status, lineage | smart regression/scenario/provider tests | none |
| S8 | Changes/environment/mobile/accessibility polish | focused frontend tests + responsive browser | none |
| S9 | Durable Worker Compose lifecycle and production profile | compose contract + launcher tests + Compose config validation | S5 |

## Execution Rules

- Each defect starts with a failing regression test and finishes with focused green tests.
- Each slice is committed locally. No push, PR, or merge occurs before first-round QA and the one-time user confirmation.
- Any discovered behavior beyond the report is recorded in the kanban and either fixed when required for an acceptance criterion or moved to a named C-condition.
- QA records command, exit code, counts, network evidence, console evidence, and viewport evidence. Visual-only screenshots are insufficient for anti-fake-success claims.

## Risks

| Risk | Control |
|---|---|
| Broad project isolation change breaks valid reads | Scope every lookup at the repository/service boundary and add same-project positive cases beside cross-project negatives. |
| Gate history contains old PASS rows | Render persisted check status honestly; do not reinterpret 0/0 as PASS. New evaluations fail closed. |
| Source refs lack a persistent rule table | Use real artifact/fragment references and honest CONTRACT_VERSION lineage rather than manufacturing rule IDs. |
| External provider and worker remain unavailable | Test failure paths locally and state the production operational prerequisites explicitly. |
| Worker container runs but silently loses one managed child | Launcher exits when either heartbeat or Temporal polling exits; Compose restarts the complete service. |
| Local deployments unexpectedly require Temporal credentials | Keep the Worker behind an explicit Compose profile enabled only by the production runtime profile. |
| Large batch creates regression risk | Keep eight reviewable commits and run both focused and full gates. |
