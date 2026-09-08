# ADR-0026: Production execution ownership and resource admission

Date: 2026-09-08. Status: accepted for opt-in implementation; production cutover
requires measured capacity and a verified complete release/rollback set.

## Context

The production host has 3723 MiB RAM and a 40 GB system disk at 94% utilization.
Independent task semaphores do not prevent browser/model/agent overlap. Process
background tasks cannot guarantee recovery after an HTTP process restart.

## Decision

- Keep one codebase with API and runner image targets. API handles reads and
  durable submissions. Registered synchronous heavy routes forward to the private
  runner, preserving existing authentication, project scope, bodies and streams.
  Unavailable runner returns 503 without unsafe local fallback or automatic replay.
- Runner owns consumer lifecycles and schedules. Additive PlanExecutionJob records
  persist before acknowledgment; owner-scoped claims/heartbeats prevent duplicates.
  Pending work survives restart; abandoned running work fails explicitly.
- Use kernel file locks on shared local storage for one heavy execution slot and
  a separate DSH orchestration lane, so parent agents can await browser children.
  Hold leases through process termination and model reference release. Bound
  process trees and containers; file locks alone are not a memory limit.
- Preserve separate Temporal gateway ownership while sharing execution admission.
  Optional off-peak knowledge catch-up uses bounded existing batches. Keep stored
  vectors, knowledge, Wiki, graph, historical task URLs and permissions.
- Bind all release images and split configuration to an immutable manifest.
  Verify archives/capacity before import and import the complete set before
  stopping owners. Rollback retains the compatible additive database schema and
  starts old application images directly, bypassing their Alembic launchers that
  cannot resolve newer revision IDs. This does not authorize destructive migrations.
- Cleanup protects running/stopped container references, aliases, current/rollback
  releases and recent assets. Apply requires an unchanged preview digest and the
  shared deployment lock. Never broaden deletion automatically to meet capacity.

## Consequences and validation

Model reload adds latency; explicit reference release does not guarantee native
allocator RSS returns immediately. Measure persistent HTTP processes, cold-cache
peaks and mixed DSH/Temporal workloads before selecting production limits. Image
split isolates ownership but does not promise a smaller complete installed set.
Rollback compatibility remains a release criterion for every later schema change.

Evidence and remaining rollout gates are maintained in
`work-logs/batch-production-capacity-guard-qa-report.md` and
`work-logs/production-execution-entry-audit.md`. The base combined deployment stays
available; enabling the execution overlay requires explicitly supplied limits.
