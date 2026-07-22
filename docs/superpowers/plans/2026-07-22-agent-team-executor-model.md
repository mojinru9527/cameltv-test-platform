# Agent Team Executor Model Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Separate the Agent Team workflow identity from the Claude Code/Codex executor identity and verify both throughout local push and PR delivery.

**Architecture:** Version 2 worktree metadata records `workflow` and `executor`; task directories remain executor-bound so concurrent tools stay isolated. Verification and PR audit accept the new fields while reading legacy `owner` metadata for existing worktrees. The Agent Team launcher requires an explicit Claude/Codex executor because Git cannot reliably infer the calling AI process.

**Tech Stack:** PowerShell 7, Git hooks (POSIX sh), GitHub CLI, GitHub Actions YAML, Markdown governance files.

---

### Task 1: Define the failing identity tests

**Files:**
- Modify: `scripts/git/test-ai-worktree-tools.ps1`

- [x] Add assertions that direct Claude/Codex entries return `Workflow=direct` and their fixed executor.
- [x] Add an Agent Team launch with `-Executor codex` and assert `Workflow=agent-team`, `Executor=codex`, and directory `codex-agent-team-isolation`.
- [x] Verify `-ExpectedWorkflow agent-team -ExpectedExecutor codex` succeeds and both mismatch cases fail.
- [x] Run `pwsh scripts/git/test-ai-worktree-tools.ps1` and expect failure because the current scripts expose only `Owner`.

### Task 2: Write version 2 metadata

**Files:**
- Modify: `scripts/git/new-ai-worktree.ps1`
- Modify: `scripts/git/start-claude-task.ps1`
- Modify: `scripts/git/start-codex-task.ps1`
- Modify: `scripts/git/start-agent-team-task.ps1`

- [x] Replace the creator identity input with executor plus workflow, retaining `-Owner` as a compatibility alias.
- [x] Write `schema_version=2`, `workflow`, and `executor`; do not write `owner` for new worktrees.
- [x] Keep direct launchers fixed to `workflow=direct` and their executor.
- [x] Require `-Executor claude|codex` on the Agent Team launcher and set `workflow=agent-team`.
- [x] Run the focused self-test and expect the launcher assertions to pass.

### Task 3: Verify both identities and retain legacy reads

**Files:**
- Modify: `scripts/git/verify-ai-worktree.ps1`
- Modify: `scripts/git/audit-ai-pr.ps1`
- Inspect: `.githooks/pre-push`

- [x] Add `ExpectedWorkflow` and `ExpectedExecutor` parameters.
- [x] For version 2 metadata, require an allowed workflow/executor pair and an executor-prefixed directory.
- [x] For legacy metadata, derive direct workflow from `owner=claude|codex|human`; allow `owner=agent-team` only as an unverifiable legacy executor state.
- [x] Return and print Workflow and Executor from verification and PR audit.
- [x] Keep pre-push invoking strict metadata and clean-state verification.
- [x] Run the self-test and expect valid pushes to pass and tampered metadata/protected pushes to fail.

### Task 4: Update the governance contract

**Files:**
- Modify: `AGENTS.md`
- Modify: `.claude/skills/cameltv-agent-team/SKILL.md`
- Modify: `.claude/skills/cameltv-agent-team/DEPARTMENTS.md`
- Modify: `docs/adr/0014-single-main-trunk-ai-worktrees.md`
- Modify: `.github/pull_request_template.md`

- [x] Document Agent Team as workflow and Claude/Codex as executor.
- [x] Replace Agent Team examples with `start-agent-team-task.ps1 -Executor claude|codex`.
- [x] Replace `ExpectedOwner` audit examples with workflow/executor checks.
- [x] State that executor selection is explicit and cannot be inferred reliably from process names or code diffs.
- [x] Run `git diff --check` and scan for obsolete `ExpectedOwner agent-team` guidance.

### Task 5: Deliver through the real PR gate

**Files:**
- Modify: `work-logs/batch-34-agent-team-executor-qa-report.md`
- Modify: `work-logs/batch-34-agent-team-executor-leader-verdict.md`
- Modify: `work-logs/kanbans/DEV-batch-34-agent-team-executor.md`

- [x] Run the PowerShell parser check and `scripts/git/test-ai-worktree-tools.ps1`; expect exit code 0.
- [x] Update this worktree's ignored metadata to workflow Agent Team and executor Codex, then verify it with both expected fields.
- [x] Stage only Batch 34 files, commit, push, and create a Draft PR targeting main.
- [x] Run the basic PR audit, wait for all required checks, then run `-RequireSuccessfulChecks`.
- [ ] Record evidence, obtain Leader approval, squash merge, verify remote branch deletion, sync control main, and remove only the verified Batch 34 worktree/branch.
