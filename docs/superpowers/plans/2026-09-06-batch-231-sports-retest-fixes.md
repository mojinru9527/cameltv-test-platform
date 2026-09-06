# Batch 231 Sports Retest Fixes - Implementation Plan

1. Add red tests for Playwright zero-test/non-zero-exit outcomes and version-run zero-item behavior; implement fail-closed execution results.
2. Add cross-project API tests for every version-task nested route; scope all lookups and add a reconciliation migration for historical executed 0/0 records.
3. Add backend and frontend Gate tests; require same-mission Build+Campaign and introduce explicit non-evaluated checks.
4. Add scenario-run request/client red tests; remove duplicated route ID, expose current version ID, and centralize structured error normalization.
5. Add DSH/provider/worker readiness red tests; propagate verified health, mark fallback provenance, and prevent invisible queued work.
6. Add schedule response red test; branch toast behavior on `triggered` and `reason`.
7. Add provenance, canonical review, SMART fallback, and lineage red tests; implement each data invariant and migration.
8. Add changes/environment/API mobile/a11y red tests; implement focused UI fixes.
9. Run focused suites after every slice, then full backend/frontend/static/migration/repository gates.
10. Start local services on ports 8391/5391 and perform a fresh production-like workflow at desktop, tablet, and mobile sizes. Preserve network, console, screenshot, and result evidence.
11. Produce QA report and conditional Leader verdict, then request the repository-mandated one-time push/PR/merge confirmation.

