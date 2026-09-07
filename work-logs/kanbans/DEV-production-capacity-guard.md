# DEV - Production Capacity Guard

Workflow: agent-team | Executor: codex | Start confirmed: user "Codex"
Worktree: F:/CamelTv-worktrees/codex-production-capacity-guard
Base: origin/main | Branch: feature/production-capacity-guard

- [x] Read production facts, repository gate and inherited conditions.
- [x] Create and verify clean isolated worktree (ports 25197/28197).
- [x] Product, PM and interface design.
- [x] S1: protected cleanup and capacity helpers + tests (21 unittest cases pass).
- [x] S2: upload/import integration (PowerShell success and rejection checks pass).
- [x] S3: local QA, dry-run evidence, review (production rollout not executed).
- [ ] User batch push/PR/merge confirmation.
- [ ] Required checks, final audit, merge.
- [ ] Reviewed production application and post-checks.

Current position: awaiting required batch push/PR/merge confirmation. Added CI smoke coverage under .github/workflows to ensure
the new release-console tests actually run; worktree scope updated accordingly.
No code pushed and no production state changed. Production dry-run identifies
four image tags and four tar files; archive bytes 2851748352. Import/upload
reserve target is not yet attainable through the conservative preview alone.
Later roadmap batches may start only after this batch merges.
