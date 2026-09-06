---
title: "Batch 231 - 体育生产深度复测缺陷修复 PRD"
owner: "qa-team"
date: "2026-09-06"
status: "Approved"
mode: "full"
batch: "batch-231-sports-retest-fixes"
branch: "fix/batch-231-sports-retest-fixes"
executor: "codex"
workflow: "agent-team"
evidence: "F:/CamelTv/_review_tools/sports-retest-20260906/复测结论-20260906.md"
tags: ["batch-231", "production-retest", "anti-fake-success", "project-isolation"]
---

# Batch 231 - PRD Summary

> Product | Date: 2026-09-06 | Status: Approved

## 1. Mode And Evidence

This is a full batch. It changes execution truth semantics, API request and response contracts, tenant isolation, persisted status repair, lineage semantics, and frontend behavior. Product knowledge was searched for zero-test runs, cross-project version tasks, empty Gate evidence, DSH quota health, and SMART fallback; no directly applicable platform knowledge record was found.

The production report proves three release-blocking defects: a Playwright run with `No tests found` was marked passed, a task from project 13 was readable while project 1 was selected, and a Mission Gate displayed PASS without Build, Campaign, or execution evidence.

## 2. User Outcomes

1. A run can pass only when at least one test actually executes and the runner exits successfully.
2. Every version-task resource is scoped by the current project, including nested plans, items, runs, mutations, and compatibility routes.
3. Gate evaluation requires a valid Build and Campaign from the same Mission/project; empty denominators are NOT_EVALUATED or BLOCKED, never PASS.
4. Scenario execution accepts a route-owned scenario ID, uses the real scenario-version ID, and renders structured server errors as text.
5. Version tasks expose a usable plan review path, truthful blocked counts, repaired historical 0/0 state, and no misleading run action.
6. DSH and AI surfaces reflect provider health. A deterministic fallback is explicitly labeled with reduced-confidence provenance. Offline workers prevent or visibly block submission.
7. Duplicate schedule triggers, Coverage Guard fallback, scenario review status, source references, and lineage all report their effective state truthfully.
8. Environment detail, ChangeSet loading, mobile API filters, and icon accessibility match the production workflows in the report.
9. The Durable Runtime Worker is a managed production service: it starts with the production Compose profile, continuously renews its registration, and restarts automatically after process, Docker, or host recovery.

## 3. Acceptance Criteria

| ID | Acceptance |
|---|---|
| AC-01 | Non-zero Playwright exit, `No tests found`, or total=0 produces failed/blocked with a human-readable reason and never `passed`. |
| AC-02 | Cross-project task/detail/plan/item/run/read/write calls return not found without revealing ownership. |
| AC-03 | Gate evaluate is disabled without Build+Campaign; the backend rejects missing/mismatched selections; every zero-evidence check is NOT_EVALUATED/BLOCKED. |
| AC-04 | `POST /scenarios/{id}/runs` no longer requires `scenario_id` in the body and uses the scenario's current version; validation details cannot crash React. |
| AC-05 | Plan review/adopt/modify remains reachable; blocked runs have blocked>0 plus reason; historical executed 0/0 tasks reconcile to blocked; non-runnable tasks expose no active run action. |
| AC-06 | Provider/DSH readiness incorporates the latest connection health and quota failure; fallback results say deterministic fallback and identify their source; no worker means submission is blocked or WAITING_WORKER is explicit. |
| AC-07 | `already_running` yields a warning/info message with the existing run ID, never a success toast. |
| AC-08 | Coverage Guard FULL fallback persists all current scenario versions as selected, clears excluded items, and returns effective type FULL. |
| AC-09 | Review statuses are canonical uppercase values with Chinese labels; real non-zero source refs flow Scope -> Intent -> Contract -> Scenario/Oracle. |
| AC-10 | Lineage uses CONTRACT_VERSION for version nodes instead of mislabeling a version row as CONTRACT_RULE. |
| AC-11 | Changes page makes no `/change-sets/0` request; environment detail shows Base URL, access type, execution mode, and runner key. |
| AC-12 | At 390x844 API filters do not overlap, and task detail icon controls have accessible names. |
| AC-13 | Focused tests, full backend/frontend regressions, static/build gates, three responsive browser viewports, and a production-like end-to-end rerun pass with no false-green evidence. |
| AC-14 | Production Compose defines an opt-in `aitde-worker` service that waits for backend health, uses the managed heartbeat launcher, requires an operator-provisioned Worker Token, and has `restart: unless-stopped`; the production profile documents all required Temporal and Worker settings. |

## 4. Boundaries

- Buying DeepSeek balance is an external account action, not a code fix. The platform must fail closed and explain the quota condition.
- Executing a production deployment remains an operational action and is not authorized by this batch. This batch makes the Worker lifecycle reproducible and restart-safe; production activation still requires a one-time real Worker Token and Temporal endpoint configuration.
- Production deployment is not included. Delivery ends at merge to `main` after the repository-required confirmation and checks.
