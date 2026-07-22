# CamelTv Platform Comprehensive Audit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Audit the latest `origin/develop` across code, functional behavior, UI quality, Git/PR delivery, Agent Team reliability, and Knowledge Center requirement/production acceptance, then ship verified fixes through a feature branch and PR.

**Architecture:** Work from an isolated worktree based on `origin/develop` so active Batch 30 changes remain untouched. Treat evidence gathering and remediation as separate phases: every issue must have a reproducible check, then each approved fix gets a regression test or browser acceptance step before commit and push.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, pytest, React 18, TypeScript, Vite, Vitest, Playwright, GitHub Actions, Jenkins, Git worktrees, GitHub CLI.

---

### Task 1: Establish the clean audit baseline

**Files:**
- Read: `AGENTS.md`
- Read: `.claude/skills/cameltv-agent-team/SKILL.md`
- Read: `C-CONDITIONS.md`
- Create: `work-logs/kanbans/DEV-batch-31-platform-audit.md`

- [ ] **Step 1: Verify the branch starts at the latest remote default branch**

Run: `git fetch origin develop && git rev-parse HEAD && git rev-parse origin/develop`

Expected: both SHAs match before audit changes are created.

- [ ] **Step 2: Record the baseline and four requested workstreams**

Create the Batch 31 Dev kanban with code/function/UI audit, push workflow audit, Agent Team repeat-defect audit, and Knowledge Center requirement/production acceptance as separate slices.

### Task 2: Run reproducible static and automated checks

**Files:**
- Inspect: `test-platform-v2/backend/app/`
- Inspect: `test-platform-v2/backend/alembic/`
- Inspect: `test-platform-v2/backend/tests/`
- Inspect: `test-platform-v2/frontend/src/`
- Inspect: `test-platform-v2/frontend/package.json`
- Create: `work-logs/reviews/QA-batch-31-platform-audit.md`

- [ ] **Step 1: Run backend import, migration, lint, and test checks**

Run from `test-platform-v2/backend`:

```bash
python -c "import app.main"
python -m alembic heads
python -m ruff check app
python -m pytest tests -q
```

Expected: import succeeds, exactly one Alembic head exists, lint exits zero, and tests pass. Any baseline failure is recorded with the exact command and first actionable traceback.

- [ ] **Step 2: Run frontend type, build, lint, and component checks**

Run from `test-platform-v2/frontend`:

```bash
npm ci
npm run typecheck
npm run build
npx eslint src --ext .ts,.tsx
npx vitest run
```

Expected: every command exits zero. Existing failures are classified separately from regressions introduced by Batch 31.

- [ ] **Step 3: Scan for security, reliability, and maintainability hazards**

Inspect authentication/authorization boundaries, secret handling, unsafe subprocess/file/network inputs, broad exception swallowing, transaction boundaries, async lifecycle cleanup, duplicate API requests, and mismatches between API schemas and frontend consumers.

### Task 3: Validate local functionality and UI quality

**Files:**
- Inspect: `test-platform-v2/frontend/src/router/`
- Inspect: `test-platform-v2/frontend/src/pages/`
- Inspect: `test-platform-v2/frontend/src/components/`
- Inspect: `test-platform-v2/backend/app/api/v1/`
- Update: `work-logs/reviews/QA-batch-31-platform-audit.md`

- [ ] **Step 1: Start the backend and frontend from the clean worktree**

Expected: backend health endpoint responds successfully and the Vite application loads without console errors.

- [ ] **Step 2: Exercise the primary authenticated journeys**

Verify login/logout, project switching, workbench navigation, requirements, test cases, plans, defects, API tests, UI tests, reports, Knowledge Center, and Agent Workbench. Record loading, empty, success, validation, permission, and error states.

- [ ] **Step 3: Audit accessibility, responsive behavior, performance, and theming**

Verify keyboard operation, accessible names, focus visibility, contrast, desktop/tablet/mobile overflow, touch targets, repeated requests, expensive rendering, semantic tokens, and light/dark/theme switching.

### Task 4: Audit Git push and PR enforcement

**Files:**
- Inspect: `AGENTS.md`
- Inspect: `.github/workflows/pr-check.yml`
- Inspect: `.github/workflows/develop-import-smoke.yml`
- Inspect: `.github/pull_request_template.md`
- Inspect: `Jenkinsfile`
- Inspect: `.claude/skills/cameltv-agent-team/SKILL.md`

- [ ] **Step 1: Compare documented flow with GitHub remote rulesets**

Expected: `develop` and `master` reject direct changes and require pull requests; feature/fix branches remain pushable.

- [ ] **Step 2: Verify the documented local checks are enforced or explicitly identified as manual**

Expected: discrepancies in branch names, CI triggers, non-blocking checks, merge policy, and post-merge cleanup are captured as findings.

### Task 5: Audit Agent Team repeat-defect controls

**Files:**
- Inspect: `.claude/skills/cameltv-agent-team/`
- Inspect: `work-logs/`
- Inspect: `C-CONDITIONS.md`
- Inspect: `docs/common-pitfalls.md`
- Inspect: recent Knowledge Center commits and pull requests

- [ ] **Step 1: Trace repeated defects across batches and fixes**

Compare issue descriptions, files, tests, QA evidence, Leader conditions, commits, and later regressions. Distinguish true recurrence from incomplete acceptance, stale tests, and parallel-branch overwrite.

- [ ] **Step 2: Test whether the pipeline prevents recurrence in practice**

Check that conditions are closed only with evidence, QA includes reproducible tests/screenshots, fixes add regression coverage, branches start from current `origin/develop`, and later PRs retain earlier fixes.

### Task 6: Accept the Knowledge Center against Lanhu and production

**Files:**
- Inspect: `test-platform-v2/frontend/src/pages/knowledge/`
- Inspect: `test-platform-v2/backend/app/api/v1/knowledge.py`
- Inspect: `test-platform-v2/backend/app/services/knowledge/`
- Create: `work-logs/batch-31-platform-audit-qa-report.md`

- [ ] **Step 1: Extract verifiable requirements from the supplied Lanhu prototype**

Record user roles, information architecture, visible fields, interactions, states, navigation, and acceptance criteria. If authentication is required, use the available signed-in browser session and report only genuinely inaccessible material as blocked.

- [ ] **Step 2: Inspect `https://www.camel1.tv/` without destructive production actions**

Use read-only navigation and safe form validation. Do not create, delete, publish, execute, or mutate production records unless the user separately authorizes the exact action.

- [ ] **Step 3: Compare requirement, implementation, and production behavior**

Produce a requirement-to-result matrix with PASS, FAIL, PARTIAL, or BLOCKED; attach browser evidence and severity to every mismatch.

### Task 7: Implement and verify scoped fixes

**Files:**
- Modify only files directly tied to confirmed P0/P1/P2 findings.
- Add regression tests beside the affected backend service/API or frontend component.

- [ ] **Step 1: Add a failing regression test for each accepted defect**

Expected: the focused test fails for the documented reason before production code changes.

- [ ] **Step 2: Apply the smallest behavior-preserving fix**

Expected: no unrelated formatting, refactoring, dependency upgrades, or feature expansion.

- [ ] **Step 3: Re-run focused and full relevant checks**

Expected: focused regression tests pass, then the applicable backend/frontend suites, build, and browser acceptance pass.

### Task 8: Complete Agent Team evidence and publish through PR

**Files:**
- Create: `work-logs/batch-31-platform-audit-prd-summary.md`
- Create: `work-logs/batch-31-platform-audit-pm-plan.md`
- Create: `work-logs/batch-31-platform-audit-design-spec.md`
- Update: `work-logs/kanbans/DEV-batch-31-platform-audit.md`
- Create: `work-logs/batch-31-platform-audit-qa-report.md`
- Create: `work-logs/batch-31-platform-audit-leader-verdict.md`

- [ ] **Step 1: Review staged scope and secrets**

Run: `git diff --cached --check && git diff --cached --name-only`

Expected: no whitespace errors, generated artifacts, secrets, databases, backups, or unrelated files.

- [ ] **Step 2: Commit and push only the Batch 31 branch**

Run: `git push -u origin feature/batch-31-platform-audit`

Expected: push succeeds without updating `develop` or `master`.

- [ ] **Step 3: Create a pull request targeting `develop`**

Expected: PR contains the evidence matrix, test results, known blockers, risk level, and links to all six Agent Team artifacts.
