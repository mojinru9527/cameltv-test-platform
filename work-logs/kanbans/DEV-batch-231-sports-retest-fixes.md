---
title: "DEV Kanban - Batch 231 Sports Retest Fixes"
batch: "batch-231-sports-retest-fixes"
branch: "fix/batch-231-sports-retest-fixes"
executor: "codex"
workflow: "agent-team"
mode: "full"
status: "IN_PROGRESS"
updated: "2026-09-06"
---

# Batch 231 Dev Kanban

| Slice | State | Evidence / Notes |
|---|---|---|
| Product / PM / Design | DONE | PRD, PM plan, design spec, and implementation plan created. KB search found no directly applicable record. |
| S1 Execution truth | DONE | Red: 4 expected failures. Green: `pytest tests/test_playwright_executor.py tests/test_version_task.py -q` = 70 passed. Zero tests and non-zero exits fail; empty version plan is 1/1 blocked. |
| S2 Tenant isolation/history | DONE | 20 cross-project API cases pass; migration repairs latest historical 0/0 to blocked 1/1 and is idempotent; backend 68 and frontend wizard/run 14 tests pass. |
| S3 Mission Gate | DONE | Backend 45 and frontend 12 focused tests pass. Build+Campaign are mandatory and matched; checks persist PASS/FAIL/NOT_EVALUATED/BLOCKED; zero execution is INCONCLUSIVE. |
| S4 Scenario execution | DONE | Red: backend 2 and frontend 3 failures. Green: backend 15, frontend 29 tests, and frontend typecheck pass. Run body no longer repeats path scenario ID; the UI sends the persisted current version ID; both API clients normalize structured errors. |
| S5 AI/DSH/Worker | DONE | Red: backend 7 and frontend 2 expected failures. Green: backend 84 and frontend 14 tests; F821 and typecheck pass. DSH failures update shared AI health, verified quota failure blocks submission, deterministic Mission output carries visible provenance/confidence, and offline Durable Worker rejects Run creation before persistence. |
| S6 Schedule trigger | DONE | Red: page regression failed on missing warning. Green: 4 page tests and frontend typecheck pass. `already_running` now reports that no run was created and includes the existing Run ID. |
| S7 Provenance/SMART/Lineage | DONE | Red: 5 focused failures. Green: 51 related-domain tests plus 8 migration checks pass; F821 passes. Review statuses are canonical, source refs keep positive persisted IDs, unsafe SMART selections atomically materialize FULL, and lineage uses `CONTRACT_VERSION`. |
| S8 UI hardening | DONE | Red: 3 focused failures. Green: 6 frontend tests and typecheck pass. Removed `/change-sets/0`, exposed four environment execution fields, and stopped mobile service tabs from shrinking. Existing API task eye-button accessible-name regression also passes. |
| S9 Managed Worker lifecycle | IN_PROGRESS | User added automatic restart and always-online requirement before delivery. Previous completion confirmation and QA closeout are invalidated; adding Compose/profile contracts and rerunning affected gates. |
| QA responsive rework | DONE | Visible 390px review found task-row collision and page shift missed by root-overflow checks. TDD added responsive task rows, tab-owned scrolling, geometry/scroll assertions, and a clean after-fix screenshot. |
| QA focused/full/browser | DONE | Backend 2483 passed; frontend 153 files/686 tests passed; build/type/lint/F821/migrations passed; 10 screenshots at 1440/768/390 with zero HTTP/console errors. Live DSH and offline-Worker probes persisted no task/Run. |
| Leader verdict | REOPENED | S9 scope added after the prior local closeout. Leader must review refreshed QA evidence before a new delivery confirmation. |

## External Preconditions

- DeepSeek account balance must be restored by an authorized operator before real AI/DSH production success can be retested.
- Production activation requires a one-time valid Worker Token and reachable Temporal endpoint; after activation Compose owns restart and the Worker owns continuous heartbeat.
- No production deployment is authorized in this batch.
