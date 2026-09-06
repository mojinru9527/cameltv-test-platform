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
| S2 Tenant isolation/history | TODO | All version-task nested routes; historical 0/0 repair. |
| S3 Mission Gate | TODO | Build+Campaign requirement; no 0/0 PASS. |
| S4 Scenario execution | TODO | 422 contract, real version ID, structured errors. |
| S5 AI/DSH/Worker | TODO | Quota-aware readiness, fallback label, offline-worker gate. |
| S6 Schedule trigger | TODO | already_running feedback. |
| S7 Provenance/SMART/Lineage | TODO | canonical review, refs, FULL materialization, node type. |
| S8 UI hardening | TODO | changes 0 request, environment details, mobile filters, eye button name. |
| QA focused/full/browser | TODO | Ports 8391/5391; 1440/768/390 evidence. |
| Leader verdict | TODO | Conditional until required checks and final audit pass. |

## External Preconditions

- DeepSeek account balance must be restored by an authorized operator before real AI/DSH production success can be retested.
- Production `aitde-worker` must be restored by operations before queued Mission runs can complete.
- No production deployment is authorized in this batch.
