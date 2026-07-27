# Master Security, User Manual, and Test Deployment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 清理测试平台中的账号密码与运行时敏感信息，补齐用户使用手册，将已验证功能合并到 `master`、推送 GitHub，并发布到当前测试平台实例。

**Architecture:** 代码仓库只保存无密钥配置模板，真实 JWT、管理员密码、AI Key、蓝湖凭据和通知地址通过未跟踪的 `.env` 或平台加密变量注入。先在功能分支完成安全清理、文档与回归，再合入最新 `origin/master`，最后合并到本地 `master`、推送并重启本机测试平台的 FastAPI/Vite 服务。

**Tech Stack:** Git/GitHub、FastAPI、React 18、TypeScript、Vite、Docker Compose、pytest、Vitest、Playwright、PowerShell。

---

### Task 1: Remove deploy-time plaintext secrets

**Files:**
- Modify: `.gitignore`
- Modify: `test-platform-v2/deploy/docker-compose.yml`
- Modify: `test-platform-v2/deploy/.env.example`
- Modify: `test-platform-v2/deploy/README.md`
- Modify: `test-platform-v2/deploy/sync-and-restart.bat`

- [ ] **Step 1: Add a secret-scan baseline**

Run a tracked-file scan that reports only file names and line numbers for private keys, non-placeholder API keys, phone/account credentials, passwords embedded in Compose defaults, `.env` files, VPN profiles, model caches, SQLite files, and generated reports.

- [ ] **Step 2: Make Compose require external secrets**

Use `${SECRET_KEY:?SECRET_KEY is required}` and `${ADMIN_PASSWORD:?ADMIN_PASSWORD is required}` for mandatory production values. Pass `AI_API_KEY`, `LANHU_USERNAME`, `LANHU_PASSWORD`, SMTP values, and notification values only from environment variables with empty defaults; never include real-looking fallback values.

- [ ] **Step 3: Expand the environment template safely**

Document every supported variable with an empty value or descriptive placeholder. Keep `.env.example` trackable and ensure the real `.env` remains ignored.

- [ ] **Step 4: Remove credential-based health checks**

Change deployment validation to call `/health` and module import checks only. Do not embed or echo a login password in scripts or README output.

- [ ] **Step 5: Ignore runtime-only artifacts**

Ignore `test-platform-v2/backend/storage/models/`, generated storage reports, Playwright run artifacts, local databases, `.ovpn`, and TypeScript build metadata. Preserve unrelated local changes outside the commit.

### Task 2: Remove frontend default credentials

**Files:**
- Modify: `test-platform-v2/frontend/src/pages/login/index.tsx`
- Create: `test-platform-v2/frontend/src/pages/login/__tests__/LoginSecurity.test.tsx`
- Modify: `test-platform-v2/frontend/e2e/smoke.spec.ts`

- [ ] **Step 1: Add the failing login security test**

Assert that username/password inputs start empty and the page does not render a reusable default password.

- [ ] **Step 2: Verify the test fails before implementation**

Run `npm test -- --run src/pages/login/__tests__/LoginSecurity.test.tsx` and expect failure against the current prefilled form.

- [ ] **Step 3: Remove prefilled credentials and public hints**

Initialize both fields with empty strings and replace the default-account hint with first-login instructions that point to the administrator-provided account.

- [ ] **Step 4: Make E2E credentials environment-only**

Read `E2E_USERNAME` and `E2E_PASSWORD`; skip the authenticated smoke scenario when they are absent.

- [ ] **Step 5: Verify the security test passes**

Run the focused Vitest file and confirm all assertions pass.

### Task 3: Publish the user manual

**Files:**
- Create: `test-platform-v2/docs/测试平台使用手册.md`
- Modify: `test-platform-v2/README.md`
- Modify: `test-platform-v2/docs/onboarding.md`
- Modify: `test-platform-v2/docs/DEV-Test5-使用与授权清单.md`

- [ ] **Step 1: Write the operator section**

Document first deployment, secure `.env` creation, database migration, startup, health checks, backup, upgrade, rollback, and credential rotation without including real values.

- [ ] **Step 2: Write the ordinary-user workflow**

Document login, project switching, environment/encrypted variables, requirement ingestion, RAG search, API import/debug/tasks, UI automation, audio/video metrics, plans, reports, defects, DingTalk/SMTP notification, audit, and logout.

- [ ] **Step 3: Document safety boundaries**

Explain that imported cases are candidates, production/test writes require explicit authorization, delete/transaction/publish actions remain disabled unless separately approved, and secrets must stay in encrypted variables or `.env`.

- [ ] **Step 4: Link the manual from active entry documents**

Replace active default-password instructions with the new manual and administrator-provided first-login credentials.

### Task 4: Validate the release candidate

**Files:**
- Test: `test-platform-v2/backend/tests/`
- Test: `test-platform-v2/frontend/src/**/*.test.ts*`
- Test: `test-platform-v2/backend/tests/playwright/specs/production-smoke.spec.ts`
- Test: `test-platform-v2/backend/tests/playwright/specs/production-web-smoke.spec.ts`

- [ ] **Step 1: Run backend regression**

Run the focused changed-module suite and then `pytest tests -q`; expect zero failures.

- [ ] **Step 2: Run frontend regression and build**

Run the focused security/API/UI tests, the full Vitest suite, and `npm run build`; expect zero failures and a successful Vite build.

- [ ] **Step 3: Run secret scans**

Scan staged files and all tracked non-test runtime/config/docs files. Allow obvious test fixtures only; reject real-looking keys, phone credentials, `.env`, `.ovpn`, database, cache, or generated report content.

- [ ] **Step 4: Review the staged diff**

Use `git diff --cached --check` and inspect staged file names so only platform source, migrations, tests, safe deployment templates, and documentation are committed.

### Task 5: Merge and push master

**Files:**
- Git refs: `feature/apitest-uitest-realization`, `origin/master`, `master`

- [ ] **Step 1: Commit the release candidate on the feature branch**

Create a single reviewed release commit covering the verified platform functionality, secret cleanup, tests, and manual.

- [ ] **Step 2: Merge the latest remote master into the feature branch**

Fetch `origin/master` over HTTPS, merge it without discarding either side, resolve conflicts, and rerun the security scan plus focused tests.

- [ ] **Step 3: Merge the feature branch into local master**

Update local `master` to `origin/master`, merge the release candidate with a merge commit, and confirm `master` contains the release commit.

- [ ] **Step 4: Push master to GitHub**

Use authenticated GitHub transport, verify the remote `master` SHA equals the local `master` SHA, and do not force-push.

### Task 6: Deploy and verify the test platform

**Files:**
- Runtime: `test-platform-v2/backend`
- Runtime: `test-platform-v2/frontend`

- [ ] **Step 1: Preserve the current data store**

Copy the current SQLite database to a timestamped local backup outside Git before restarting services.

- [ ] **Step 2: Restart the backend and frontend**

Stop only the processes listening on ports 8000 and 5173 after confirming their command lines point to this workspace. Start replacement processes hidden from the correct working directories.

- [ ] **Step 3: Verify health and browser access**

Confirm `/health` is 200, the login page loads, the API test page no longer crashes, and the release functionality is visible through the Web frontend.

- [ ] **Step 4: Record deployment evidence**

Capture the deployed Git SHA, service PIDs, health result, regression counts, and remaining external blockers (DingTalk Webhook and optional Konfi admin token) in the final handoff.
