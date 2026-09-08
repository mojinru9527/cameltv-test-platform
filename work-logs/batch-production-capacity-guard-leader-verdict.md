# Production Capacity Guard - Leader Verdict

Date: 2026-09-07 | Executor: codex
Status: implementation review complete. The final merge verdict is recorded in
PR 415 only after the latest required checks and successful final audit.

Product, PM, interface design, Dev and local QA artifacts exist. The local
checks support incremental implementation, not a claim that production space
has already been reclaimed. The user authorized all four roadmap phases and
push/PR/final merge together. Final approval remains pending complete-scope QA,
latest required remote checks and successful final PR audit.

## Review

- Initial capacity scope is now part of the authorized four-phase delivery;
  do not guess memory limits from idle samples. Explicit rollback/current pairs, aliases, container references and
  recent assets are protected. No generic prune, forced image removal or
  database/volume/container deletion is implemented.
- Cleanup is preview-first and approval-bound; fresh state is rechecked.
  Coordinating lock also covers release-console deploy/rollback. Existing
  unpatched production console must be upgraded before apply; pause other
  out-of-band release writers and pin pending deployments.
- New tests are executed in the required delivery workflow, not merely added
  to a previously undiscovered test folder.
- Production disk target remains unresolved. Do not extend deletion to the
  stopped legacy worker or call the overall optimization complete.
- All four implementation phases stay on the same branch and PR 415. Local full
  regression, real complete-bundle verification/import, PostgreSQL/Temporal topology
  transitions, DSH/member/browser/model overlap and product consolidation now have
  executed evidence. Failed initial rollback/CI attempts and their repairs are
  documented in QA; they are not silently treated as successful runs.
- API 384 MiB, runner 1536 MiB and worker 512 MiB are candidates verified in the
  isolated topology, not proof of production long-task capacity. The rollout plan
  requires host headroom, an observed canary and a preserved rollback path.
- Code merge and production release are separate gates. Production remains blocked
  by disk reserve; no protected assets may be removed to force publication. Cloud
  expansion incurs cost and awaits user input. No production benefit is claimed.

## 流程回写

| Finding | Action | Location |
|---|---|---|
| Aggregate image sizes overstate cleanup savings | Record unique/shared storage and actual delta requirement | QA report and release-console README |
| `/health` can be a frontend SPA fallback | Use `/api/v1/open/health` response body plus container health | QA report |
| Existing CI ignored separate console tests | Add Python and PowerShell smoke steps | .github/workflows/ai-delivery-policy.yml |
| No connected credentialed KB ingest tool | Preserve repository evidence; external knowledge ingestion not claimed | PRD/QA/Leader artifacts |
| Old image cannot resolve a newer Alembic revision during rollback | Override rollback startup, preserve additive schema, rehearse actual old image | ADR-0026 and topology smoke |
| Missing local submodule masked deployment contract failures | Initialize submodule and execute all 40 affected tests | QA remote regression follow-up |

No shared skill files were changed; no skill changelog is needed. Outstanding
rollout items remain in the current kanban, not mislabeled as closed conditions.

## Retro card

Original capacity estimate: 2 hours; expanded four-phase scope continued across
2026-09-07 to 2026-09-09, with no reliable active-hours timesheet. Do not retain
the original 0.3-hour figure as the total effort. New P1 defects found and repaired:
2 (migration reconciliation and old-image rollback launcher). Operational P1: disk
reserve still open. Rework: at least four validation/repair rounds across the
expanded delivery. Causes: migration history, stale contracts, missing local
submodule and local Docker startup tooling. Next prevention: rehearse the previous
real image against the new schema before approving any additive migration release.
