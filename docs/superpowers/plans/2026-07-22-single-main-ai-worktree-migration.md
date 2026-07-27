# Single Main Trunk and AI Worktree Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Preserve every existing local change, consolidate the audited platform into one protected `main` trunk, retire `develop` and legacy `master`, and make Claude Code, ChatGPT/Codex, and Agent Team use isolated task worktrees without affecting the running local platform.

**Architecture:** Keep `F:\CamelTv` untouched as the current runtime/dirty workspace during migration. Perform source changes in `F:\CamelTv-batch31-audit`, protect all refs with Git bundles and dirty-file archives, merge through PR #56, rename the verified remote `develop` branch to `main`, and create a new clean `F:\CamelTv-control` worktree. Repository-owned PowerShell helpers and a pre-push hook enforce task branches, clean baselines, per-worktree metadata, and protected-branch safety.

**Tech Stack:** Git worktree, GitHub CLI/API, GitHub Actions, PowerShell 7, POSIX shell hook, Jenkins Pipeline, Markdown/ADR, FastAPI/pytest, React/TypeScript/Vitest/Vite.

---

### Task 1: Create and verify recoverable backups

**Files:**
- Create outside repository: `F:\CamelTv-safe-backup\<timestamp>\cameltv-all-refs.bundle`
- Create outside repository: `F:\CamelTv-safe-backup\<timestamp>\cameltv-dirty-files.zip`
- Create outside repository: `F:\CamelTv-safe-backup\<timestamp>\lanhu-mcp-all-refs.bundle`
- Create outside repository: `F:\CamelTv-safe-backup\<timestamp>\lanhu-mcp-dirty-files.zip`
- Create outside repository: `F:\CamelTv-safe-backup\<timestamp>\SHA256SUMS.txt`

- [ ] **Step 1: Record source state without changing it**

Run `git status -sb`, `git worktree list --porcelain`, nested `lanhu-mcp` status, all refs, open PRs, current default branch, rulesets, and running service processes.

- [ ] **Step 2: Back up all Git refs**

Run `git bundle create <backup>/cameltv-all-refs.bundle --all` and `git -C lanhu-mcp bundle create <backup>/lanhu-mcp-all-refs.bundle --all`.

- [ ] **Step 3: Archive tracked and untracked dirty files**

Archive the exact paths returned by porcelain status for the parent and nested repository. Do not include `.git`, dependency caches, or unrelated worktrees.

- [ ] **Step 4: Verify recovery artifacts**

Run `git bundle verify` for both bundles, compute SHA-256 for every artifact, and list both ZIP archives. Expected: both bundles valid, all dirty paths present, no source file changed.

### Task 2: Reconcile the dirty runtime workspace with PR #56

**Files:**
- Inspect only: `F:\CamelTv\test-platform-v2\frontend\package*.json`
- Inspect only: `F:\CamelTv\test-platform-v2\frontend\src\lib\icons.ts`
- Inspect only: `F:\CamelTv\test-platform-v2\frontend\src\pages\requirement\components\*.tsx`
- Inspect only: `F:\CamelTv\test-platform-v2\frontend\src\components\ui\*.tsx`
- Inspect only: `F:\CamelTv\test-platform-v2\backend\test_all_apis.py`
- Create: `work-logs/batch-32-main-trunk-migration-local-reconciliation.md`

- [ ] **Step 1: Compare every dirty parent-repository file with PR #56 ignoring line-ending-only differences**

Expected classifications: identical, PR #56 supersedes, unique production change, or temporary/debug artifact.

- [ ] **Step 2: Preserve unique production changes only**

Apply unique behavior to the isolated audit worktree with `apply_patch`; do not reset, clean, checkout, or stage `F:\CamelTv`.

- [ ] **Step 3: Document reconciliation**

Record each dirty path, its classification, backup location, and merge decision. Nested `lanhu-mcp` remains an independent untouched repository.

### Task 3: Add enforceable single-trunk/worktree tooling

**Files:**
- Create: `.gitmodules`
- Create: `scripts/git/new-ai-worktree.ps1`
- Create: `scripts/git/verify-ai-worktree.ps1`
- Create: `scripts/git/install-git-guardrails.ps1`
- Create: `.githooks/pre-push`
- Modify: `.gitignore`
- Create: `docs/adr/0014-single-main-trunk-ai-worktrees.md`

- [ ] **Step 1: Add worktree preflight assertions**

The verifier must resolve the repository root dynamically, reject `main`, `master`, or `develop` as a development branch, require `feature/*`, `fix/*`, `hotfix/*`, or `release/*`, report dirty files, compare the branch base with `origin/main`, and print all active worktrees.

- [ ] **Step 1a: Repair the tracked Lanhu dependency metadata**

Add the missing `.gitmodules` entry for the existing `lanhu-mcp` gitlink and verify a clean recursive clone can fetch pinned commit `c9f4a43124c1e10c442a487c54c456b1ad32d65e`. Keep the existing dirty nested repository untouched.

- [ ] **Step 2: Add worktree creation helper**

The creator must fetch/prune, reject duplicate local or remote branch names and existing target directories, create from exact `origin/main`, write ignored `.ai-worktree.json` metadata with owner/task/scope/ports, and invoke the verifier.

- [ ] **Step 3: Add repository guardrail installer**

The installer must set the authenticated GitHub identity, `fetch.prune=true`, `push.default=current`, `rerere.enabled=true`, and `core.hooksPath=.githooks` without altering system Git configuration.

- [ ] **Step 4: Add pre-push protected-branch block**

The hook must reject pushes whose destination ref is `refs/heads/main`, `refs/heads/master`, or `refs/heads/develop`, while permitting task branches and tags.

- [ ] **Step 5: Test helpers in a disposable worktree**

Expected: protected-branch validation fails; valid task-branch dry run succeeds; duplicate branch and duplicate directory fail; generated metadata remains ignored.

### Task 4: Align Agent Team, Claude, CI, and Jenkins for the migration

**Files:**
- Modify: `AGENTS.md`
- Modify: `CLAUDE.md`
- Modify: `.claude/skills/cameltv-agent-team/SKILL.md`
- Modify: `.claude/skills/cameltv-agent-team/DEPARTMENTS.md`
- Modify: `.github/pull_request_template.md`
- Modify: `.github/workflows/pr-check.yml`
- Replace: `.github/workflows/develop-import-smoke.yml` with `.github/workflows/main-quality-gate.yml`
- Modify: `Jenkinsfile`
- Modify: `C-CONDITIONS.md`
- Create: `work-logs/batch-32-main-trunk-migration-{prd-summary,pm-plan,design-spec,qa-report,leader-verdict}.md`
- Create: `work-logs/kanbans/DEV-batch-32-main-trunk-migration.md`

- [ ] **Step 1: Make repository documents the source of truth**

Replace path-specific Claude Memory requirements with repository-relative instructions. Require every AI session to run the verifier before edits and to use a unique batch/log name.

- [ ] **Step 2: Switch persistent branch terminology to `main`**

All new branches start at `origin/main`; all PRs target `main`; `develop` and `master` appear only in the migration/legacy section.

- [ ] **Step 3: Make CI transitional and blocking**

During PR #56, workflows listen to both `develop` and `main`. Runtime import/F821/migration/typecheck/build and full pytest/Vitest must return non-zero on failure; legacy lint/coverage debt may remain explicitly advisory.

- [ ] **Step 4: Align Jenkins**

Docker registry push remains restricted to `main`; test commands must no longer hide failures with `|| true` where they are quality gates.

- [ ] **Step 5: Complete all Agent Team artifacts**

QA records backup validation, dirty-file reconciliation, script tests, full platform tests, CI links, branch/tag/ruleset checks, and unchanged runtime workspace evidence. Leader approval requires all mandatory checks green.

### Task 5: Validate, commit, push, and merge PR #56 into `develop`

**Files:** all files from Tasks 2–4.

- [ ] **Step 1: Run patch and credential checks**

Run `git diff --check`, explicit staged-file review, and staged credential-pattern scan.

- [ ] **Step 2: Run full backend validation**

Run import smoke, Ruff F821, Alembic head/revision tests, then full pytest. Expected: all mandatory checks pass.

- [ ] **Step 3: Run full frontend validation from a clean dependency install**

Run `npm ci`, typecheck, full Vitest, and production build. Expected: all mandatory checks pass.

- [ ] **Step 4: Commit and push explicitly scoped files**

Use the authenticated GitHub noreply identity for the commit; push only `feature/batch-31-platform-audit`.

- [ ] **Step 5: Wait for PR checks and merge**

Mark PR #56 ready only after CI is green, then squash merge through GitHub into `develop`. Do not directly push the protected branch.

### Task 6: Establish the audited baseline and rename `develop` to `main`

**Files/remote state:**
- Create remote annotated tag: `baseline-2026-07-22-audited`
- Rename remote branch: `develop` → `main`

- [ ] **Step 1: Verify the merged SHA and tag it**

Tag the exact PR #56 merge SHA and push the tag. Verify remote tag dereferences to the merge commit.

- [ ] **Step 2: Rename through the GitHub branch API**

Rename `develop` to `main` without creating a parallel copy. Expected: repository default is `main`, `origin/main` points to the baseline SHA, and `origin/develop` no longer exists.

- [ ] **Step 3: Refresh local remote metadata**

Fetch/prune and update `origin/HEAD`. Do not switch or clean `F:\CamelTv`.

### Task 7: Protect `main`, archive/delete legacy `master`, and clean repository settings

**Files/remote state:**
- Update main ruleset
- Create remote annotated tag: `legacy-master-2026-07-15`
- Delete remote branch: `master`
- Enable squash-only merging and automatic branch deletion

- [ ] **Step 1: Require PR and green quality checks on `main`**

Preserve deletion/non-fast-forward protection, require PRs, require the two clean-checkout quality jobs, and disallow bypass.

- [ ] **Step 2: Set merge policy**

Enable squash merge only and automatic deletion of merged head branches; disable merge commits and rebase merge.

- [ ] **Step 3: Archive old `master` before deletion**

Create and push `legacy-master-2026-07-15` at exact old `master` SHA `4298aad880e03af07a23e25de94c57a783bac4c0`. Verify it remotely before changing protection.

- [ ] **Step 4: Remove legacy protection and branch**

Delete the `protect-master` ruleset, delete remote `master`, fetch/prune, and verify the legacy tag remains recoverable.

### Task 8: Create the clean control worktree and complete end-to-end verification

**Files/local state:**
- Create worktree: `F:\CamelTv-control` on local `main` tracking `origin/main`
- Create and remove disposable validation worktrees under `F:\CamelTv-worktree-validation-*`

- [ ] **Step 1: Create the clean control worktree**

Expected: clean status, exact baseline SHA, `main` tracks `origin/main`, no runtime services are started from it.

- [ ] **Step 2: Install and test guardrails**

Verify identity is the GitHub user, hooks path is active, a direct `main` push is rejected locally, and a task branch can push normally.

- [ ] **Step 3: Validate two-AI isolation**

Create disposable Claude and Codex worktrees from `origin/main`, assign different ignored metadata and ports, edit different temporary ignored files, verify neither appears in the other, then remove only the disposable worktrees.

- [ ] **Step 4: Verify runtime workspace unchanged**

Compare the before/after status, hashes of every dirty parent file, nested `lanhu-mcp` status, and running service process IDs for `F:\CamelTv`. Expected: no source or runtime state change.

- [ ] **Step 5: Final remote audit**

Expected: default `main`; no remote `develop` or `master`; baseline and legacy tags present; main ruleset active with required checks; PR #56 merged; future Agent Team instructions and scripts all reference `origin/main`.
