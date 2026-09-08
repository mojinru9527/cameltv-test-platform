# Production Capacity Guard - Interface Design

Initial capacity slice uses standard-library Python and JSON for the operator
interface. The authorized combined scope additionally includes application and
product changes described in production-resource-budget-design.md and
production-execution-isolation-design.md. SSH transports base64-encoded Python
source and JSON arguments, not shell-interpolated file paths or secrets.

## Capacity admission

Reserve = max(8 GiB, archive_bytes * 3 + 2 GiB) before upload;
max(8 GiB, archive_bytes * 2 + 2 GiB) before import. Factors are conservative
admission policy, not a proof of compressed-image expansion size. Check the
release directory, Docker root and containerd root (when present), grouped by
filesystem to avoid misleading summed capacities. Require 5% free inodes
and at least 1024 when the filesystem reports inode accounting. Inspection
failure blocks. Check is a point-in-time snapshot, not a disk reservation.

## Cleanup

Release tag grammar: release-YYYYMMDD-NNNN. Allowlist only cameltv-tp-backend,
cameltv-tp-frontend and cameltv-tp-runner. Require two explicit retained complete
release sets; split sets also require their runner and retained execution YAML.
Protect two latest release tags, releases younger than 48 hours, all container
image IDs and any image having a tag outside the allowlist grammar.
Only exact regular non-symlink *-backend.tar/*-frontend.tar/*-runner.tar archives older
than 48 hours are candidates; no recursion and no backup suffixes. Execution YAML
files are retained and their checksums are bound to immutable release manifests.

Preview is the default. Apply requires the exact SHA-256 digest of a freshly
computed plan. Recheck container/image references before image deletion;
never force-delete and never call system/image/volume prune. An exclusive
host file lock coordinates this tool with release-console deploy/rollback.
Operators must pause other out-of-band deployment tools during application.

## Results

JSON report: protected tags, image-tag candidates, archive candidates,
archive bytes (exact), disk free bytes, plan digest. Image reclaimed space
is deliberately not estimated by adding image virtual sizes.
Failures exit nonzero. Partial application is reported by the process failure;
rerun preview rather than replaying approval. Retention never deletes the
database, audit trail, credentials, dumps or running/stopped containers.

## Durable asynchronous plans

Replace the untracked HTTP BackgroundTasks execution with an additive
plan_execution_job table using existing QueueSpec/atomic_claim primitives.
Persist request parameters and caller/project identity before acknowledgment;
return the job_id along with the compatible async=true field. Polling consumers
belong exclusively to the runner lifecycle. Their liveness is part of /health.
The plan's existing execution records remain the source of case results.

Pending jobs survive process restart. A claimed job has owner and heartbeat;
fresh workers cannot claim it twice. Heartbeat-expired running jobs become
failed and are not replayed automatically. Explicitly re-submit after assessing
any partial external side effects. The project-scoped execution-jobs endpoint
shows pending/running/completed/failed state and recorded failure messages.
Completed means dispatch finished, not that every test passed; result counts
retain their existing meaning, including blocked cases. The old process-only
run_async_execute_all wrapper is removed after checking it has no other callers.

## Product consolidation implementation

The existing version-task and Mission models have different lifecycle and
historical identifiers. Both remain accessible in a single `任务与报告` navigation
group, ordered as version tasks, intelligent tasks, reports and release bundles.
Defects retain their own link. The server-filtered MenuItem objects, paths and
permission codes are reused verbatim; no extra list/count requests are added.
Knowledge/Wiki/graph entry points and data remain available.

Report/trace tabs use the existing accessible Tabs component. Only the active
panel mounts its hooks, charts and dialogs. Report list, trend and coverage
requests receive the hook's AbortSignal and are cancelled when their panel
unmounts. `/report`, `/report?tab=trace`, and the existing `/trace` redirect remain
valid. This consolidates navigation without renumbering or migrating task data.
