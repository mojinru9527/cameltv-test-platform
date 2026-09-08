Production currently has a 94%-full system disk, while separate heavy-task limits
allow browser/model/orchestration workloads to overlap. This change adds protected
release retention and upload/import admission, shared host execution leases,
opt-in API/runner isolation, durable plan dispatch and quieter task/report pages.

- Release bundles bind every image config digest and the split Compose checksum.
  Registration is immutable, deployment is claimed before SSH, and rollback
  restores the target's registered combined/split topology. Current/rollback
  images, stopped-container references and non-release aliases remain protected.
- API keeps accepted asynchronous plans durable during runner outages; synchronous
  heavy calls fail with retryable 503. Runner owns consumers, models and browsers.
  DSH parents use a separate orchestration lane to avoid child admission deadlock.
- Task/report navigation retains original routes/permissions. Inactive report
  panels unmount and cancel requests. Budgeted model operations release references
  before returning the shared lease; optional knowledge catch-up runs off peak.

Validation: backend 2594 passed, 51 skipped, 1 xfailed; frontend 697 passed across
159 files; typecheck/lint/build and backend F821/route guards pass. Existing scan
warnings remain 332, HARD=0. Actual PostgreSQL migration retry/rollback preserves
data. Fresh baked API/runner images pass real Chromium, real BGE embedding,
persistent HTTP model cycles, authentication/project forwarding, runner outage
and durable task recovery. Console tests, real Compose merge and native transfer
failure checks pass. Evidence: work-logs/batch-production-capacity-guard-qa-report.md.

Draft: full DSH/Temporal mixed-memory sizing and real release topology transition
rehearsal remain required before final approval. Production still has only 2.4 GiB
free; reviewed cleanup alone cannot establish the release reserve. No production
cleanup, deployment, measured resource savings or final merge is claimed.
