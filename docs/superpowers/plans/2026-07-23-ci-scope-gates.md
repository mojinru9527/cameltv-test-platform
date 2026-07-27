# CI Scope Gates Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run only the relevant frontend/backend PR test suites while preserving the three stable required check names and conservative full-test fallbacks.

**Architecture:** A dependency-free Python classifier maps the complete PR file set to backend/frontend impact. Required workflows always trigger; their fixed-name jobs always report a result, but heavyweight setup/test steps run only for affected domains. Unknown, cross-cutting, CI, deployment, manual, and `main` push events force both domains so classification errors fail safe.

**Tech Stack:** GitHub Actions YAML, Python 3.12 standard library, PowerShell/Git guardrails, unittest.

---

### Task 1: Define the CI classification contract

**Files:**
- Add: `scripts/ci/test_classify_ci_changes.py`

- [x] Add a table-driven unittest suite for documentation/governance-only, backend-only, frontend-only, mixed, CI/deployment, unknown, empty, and force-all inputs.
- [x] Assert documentation/Git governance produces `backend=false, frontend=false`.
- [x] Assert unknown or cross-cutting paths produce `backend=true, frontend=true`.
- [x] Run `python scripts/ci/test_classify_ci_changes.py`; observed the expected `ModuleNotFoundError` before implementation.

### Task 2: Implement the fail-safe classifier

**Files:**
- Add: `scripts/ci/classify_ci_changes.py`

- [x] Implement `classify_paths(paths, force_all=False)` with normalized POSIX paths and deterministic reasons.
- [x] Treat Markdown, `docs/`, `work-logs/`, `.claude/`, `.githooks/`, `scripts/git/`, and `scripts/ci/` as platform-test-neutral.
- [x] Treat backend/frontend directories as their own domains; treat workflow/deploy/unknown/empty inputs as both domains.
- [x] Add CLI support for NUL-delimited `--files-from`, `--force-all`, and `--github-output`.
- [x] Run the unittest suite; all classification, submodule-pointer, CLI, and normalization cases pass.

### Task 3: Make required checks conditional without losing contexts

**Files:**
- Modify: `.github/workflows/main-quality-gate.yml`
- Modify: `.github/workflows/ai-delivery-policy.yml`

- [x] Add an always-triggered `detect_changes` job that compares PR base/head SHAs and uses `--force-all` for push/manual events.
- [x] Move original heavy commands into domain-conditional `backend_tests` and `frontend_tests` jobs.
- [x] Keep required names `后端全新检出与全量回归` and `前端全新检出与全量回归` on always-running aggregator jobs.
- [x] Make aggregators fail when detection or the required domain test fails, and succeed with an explicit skip summary only for an unaffected domain.
- [x] Run the classifier tests from the always-running `AI/Git 交付策略` job.

### Task 4: Scope the four extended PR jobs

**Files:**
- Modify: `.github/workflows/pr-check.yml`

- [x] Add the same detector job using the local classifier.
- [x] Run `backend-check` and `backend-check-pg` only for backend impact.
- [x] Run `frontend-check` and `frontend-a11y` only for frontend impact.
- [x] Keep workflow dispatch conservative by forcing both domains.

### Task 5: Add static workflow contract tests

**Files:**
- Modify: `scripts/ci/test_classify_ci_changes.py`

- [x] Assert all three PR workflows still trigger on `pull_request` to `main` without top-level path filters.
- [x] Assert the three ruleset context names remain present in job names.
- [x] Assert required jobs contain detector dependencies, fail-on-detector-error steps, conditional heavy steps, and lightweight skip steps.
- [x] Assert extended jobs contain domain-specific job conditions.
- [x] Parse all workflow YAML and run `git diff --check`.

### Task 6: Synchronize governance and deliver

**Files:**
- Modify: `AGENTS.md`
- Modify: `docs/adr/0014-single-main-trunk-ai-worktrees.md`
- Modify: `.claude/skills/cameltv-agent-team/SKILL.md`
- Modify: Batch 36 QA/Leader/kanban artifacts.

- [x] Document the classification matrix, unknown-path fail-safe, and full tests on `main` push/manual runs.
- [x] Record that related full suites still rerun on each PR push; unrelated domains skip.
- [x] Run local unit/static tests, push a Draft PR, and verify the real CI configuration change takes the conservative full path.
- [x] Run the basic audit, wait for first checks, and stop for the user's second Codex/final-delivery confirmation.
- [ ] After confirmation, complete final audit, mark Ready, squash merge, sync control `main`, and remove only the verified Batch 36 worktree/branch.
