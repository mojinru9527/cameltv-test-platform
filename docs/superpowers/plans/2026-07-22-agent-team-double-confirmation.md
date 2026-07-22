# Agent Team Double Confirmation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Agent Team pause for explicit Claude Code/Codex confirmation before development and again before final audit or merge.

**Architecture:** Version 3 local worktree metadata records a confirmed start identity and a pending/confirmed completion identity. Agent Team launch requires a switch that may only be supplied after the user replies in chat. Draft pushes and first CI are allowed while completion is pending; the final successful-check audit refuses Agent Team delivery until a separate completion command records the user's second confirmation. Git worktrees, branches, ports, and metadata paths provide isolation independently of whether Claude Code runs in VS Code or Codex runs in the ChatGPT desktop client.

**Tech Stack:** PowerShell 7, Git worktrees/hooks, GitHub CLI, GitHub Actions YAML, Markdown governance files.

---

### Task 1: Establish governance artifacts

**Files:**
- Add: `work-logs/batch-35-agent-team-confirmations-*.md`
- Add: `work-logs/kanbans/DEV-batch-35-agent-team-confirmations.md`

- [x] Record the user's explicit start confirmation as Codex in the ChatGPT desktop client.
- [x] Define the two hard pauses and the non-goals for this Git-only batch.
- [x] Keep all current open C conditions out of scope because no platform business code changes.

### Task 2: Add failing confirmation tests

**Files:**
- Modify: `scripts/git/test-ai-worktree-tools.ps1`

- [x] Prove Agent Team launch without `-UserConfirmedExecutor` fails without creating a branch or directory.
- [x] Prove valid Claude/Codex starts create schema v3 metadata with start confirmed and completion pending.
- [x] Prove completion without confirmation, with a mismatched executor, or while dirty is rejected.
- [x] Prove the correct completion command marks the matching executor confirmed and strict verification then succeeds.

### Task 3: Implement the two confirmation gates

**Files:**
- Modify: `scripts/git/new-ai-worktree.ps1`
- Modify: `scripts/git/start-agent-team-task.ps1`
- Modify: `scripts/git/verify-ai-worktree.ps1`
- Modify: `scripts/git/audit-ai-pr.ps1`
- Add: `scripts/git/confirm-agent-team-completion.ps1`

- [x] Write schema v3 confirmation state for new Agent Team tasks.
- [x] Require the start assertion switch before worktree creation.
- [x] Add a separate clean-worktree completion command with executor-match checks.
- [x] Preserve schema v1/v2 read compatibility while preventing legacy metadata from bypassing the final Agent Team gate.
- [x] Allow Draft push/first CI with completion pending; require completion confirmed for final successful-check audit.

### Task 4: Synchronize the operating contract

**Files:**
- Modify: `AGENTS.md`
- Modify: `.claude/skills/cameltv-agent-team/SKILL.md`
- Modify: `.claude/skills/cameltv-agent-team/DEPARTMENTS.md`
- Modify: `docs/adr/0014-single-main-trunk-ai-worktrees.md`
- Modify: `.github/pull_request_template.md`

- [x] Put both chat questions and hard-stop points into the canonical Agent Team entry.
- [x] Explain that client surfaces do not determine worktree isolation or executor identity.
- [x] Add start/completion confirmation evidence fields to PR delivery.

### Task 5: Validate through a real Draft PR

**Files:**
- Modify: Batch 35 QA, Leader, and kanban artifacts.

- [x] Pass parser, self-test, hook, YAML, documentation, and diff checks locally.
- [x] Upgrade this Batch 35 ignored metadata to schema v3 with start Codex confirmed and completion pending.
- [ ] Commit exact Batch 35 files, push the feature branch, create a Draft PR, and wait for first CI.
- [ ] Prove the basic audit passes and final audit is blocked while completion is pending.
- [ ] Stop and ask the user to reconfirm the actual executor and authorize final audit/merge.
- [ ] Only after that reply, record completion, push evidence, wait for final CI, audit, squash merge, and clean up the verified Batch 35 worktree.
