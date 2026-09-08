# Production Capacity Guard - PRD

Date: 2026-09-07 | Workflow: agent-team | Executor: codex | mode: full

## Problem and scope

Production has 3.64 GiB RAM and a 40 GB system disk at 94% utilization.
At 23:20 CST, available memory was 2.20 GiB; two days of ten-minute samples
cannot rule out short memory peaks. Container storage occupied approximately
25 GB and release archives 2.7 GB. No production deletion is justified solely
by image size, table estimates, or a stopped container's exit code.

The user expanded the original capacity-only scope to all four phases of the
implementation roadmap, delivered together in PR 415. This full batch now covers
disk protection, shared resource admission, API/runner isolation, and task/report
entry consolidation with on-demand/off-peak knowledge processing.

## Success criteria

- Preview cleanup with exact tags/files, retained versions and a plan digest.
- Protect all container image references (including stopped containers), all
  non-release aliases, explicitly pinned current/rollback versions, recent
  releases and recent archives. Never prune volumes, databases or backups.
- Reject stale cleanup approval; Docker deletion must not use force.
- Check free bytes and inodes before upload and before image import; fail
  closed on inspection errors. Preserve a working rollback path.
- Operational target: at least 8 GiB free after approved cleanup. Report actual
  measured change rather than summing shared image sizes.
- Heavy execution shares a same-host budget; browser children and DSH parents
  cannot deadlock by competing for the same lane. Cancellation and crashes must
  release owned resources without orphaned child processes.
- API stays usable during runner failure. Accepted queued work persists before
  acknowledgment. Unclaimed work survives restarts; interrupted running work is
  reported explicitly without unsafe automatic replay of external side effects.
- Separate image targets, shared artifacts, measured limits, health checks and
  complete-set release/rollback preserve production functionality.
- One task/report navigation preserves existing deep links and permissions;
  populated knowledge/Wiki/graph features remain available. Optional knowledge
  work runs on demand or off peak. Validate historical/new task mapping.
- Complete all affected local and required CI checks, final audit, single squash
  merge, main checks and reviewed production optimization with measured evidence.

## Acceptance stories

- Given current and rollback releases, when preview runs, both image pairs
  exist and are excluded from candidates, even through a shared image ID.
- Given a preview, when tags/containers/files change, applying its old digest
  fails before deletion.
- Given insufficient capacity, when upload/deploy is requested, no upload,
  Docker load, retag or service recreation happens after the failed check.

## Non-goals and inherited conditions

No business data deletion, guessed memory limits, blanket container/image prune,
or removal of populated knowledge features. Additive schema changes needed for
durable execution are in the expanded scope. C-CONDITIONS.md was searched for storage/capacity dependencies; C140-1
concerns the obsolete Railway storage deployment and is not closed here.
Other business/UI conditions are included only where required by the authorized
task/report consolidation, rather than reopening unrelated feature work.

## Skills and delivery

cameltv-agent-team: six artifacts and isolated worktree; writing-plans:
sequenced roadmap; karpathy-guidelines: scoped changes; cameltv-deploy:
read-only production inventory. Local repository knowledge is used; no
credentialed knowledge-ingest connector is available in this session.
QA precedes the user's one-time push/PR/merge confirmation. Production
cleanup is a separately enumerated operational action, not a code merge.
