# Batch 57 Environment Targets and Acceptance Implementation Plan

> **Superseded on 2026-07-29:** 用户将运行拓扑从 local/test/production
> 调整为仅 local/production。后续实施与验收以
> `2026-07-29-batch-57-local-production-and-batch56-closure.md` 为准。

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** 让测试平台 local/test/production 三套实例分别绑定固定访问地址和独立数据库，配置一次后通过固定地址访问，不再运行中手动切换数据库，并如实承接 Batch 56 的生产验收遗留。

**Architecture:** 不增加页面内热切数据库能力；SQLAlchemy engine 在进程启动时绑定数据库，因此每个环境保持独立前后端实例和独立数据库。使用三份无密钥 profile 模板、三个本地忽略的真实 profile 和一个启动器统一装载配置；local 使用 Vite + Uvicorn，test/production 使用独立 Compose project、volume 和 PostgreSQL。`/environment` 继续只管理被测系统的 dev/test/staging/prod 地址和变量。

**Tech Stack:** PowerShell 7, FastAPI/Pydantic Settings, React/Vite, Docker Compose, PostgreSQL 16, SQLite, Pytest.

---

## File map

- Create `test-platform-v2/config/runtime/local.env.example` — local 固定地址、端口、SQLite 和安全默认模板。
- Create `test-platform-v2/config/runtime/test.env.example` — test 固定 HTTPS 地址、独立 Compose project 和 PostgreSQL 模板。
- Create `test-platform-v2/config/runtime/production.env.example` — production 固定 HTTPS 地址、独立 Compose project 和 PostgreSQL 模板。
- Create `test-platform-v2/scripts/start-platform-environment.ps1` — 装载指定 profile，幂等启动或查询 local/test/production 实例。
- Create `test-platform-v2/backend/tests/test_runtime_environment_profiles.py` — profile 隔离、安全门禁和固定地址契约。
- Modify `test-platform-v2/deploy/docker-compose.yml` — 移除固定容器名，并把运行模式/Cookie 安全项交给 profile 的必填值。
- Modify `test-platform-v2/backend/tests/test_deploy_compose_contract.py` — 锁定 Compose 多实例和生产安全契约。
- Modify `test-platform-v2/backend/.env.example` — 指向 runtime profiles，保留单实例兼容方式。
- Modify `test-platform-v2/frontend/.env.example` — 说明每实例只走同源 `/api/v1`，不跨环境直连。
- Modify `test-platform-v2/README.md` — 写明三套固定地址、独立数据库和启动方式。
- Modify `test-platform-v2/deploy/README.md` — 写明 test/production profile 的一次配置、Compose project 隔离和发布命令。
- Create `test-platform-v2/work-logs/batch-57-environment-targets-and-batch56-acceptance.md` — 记录实施、自检和 Batch 56 仍未关闭的正式阻断。

### Task 1: Lock the runtime-profile contract with tests

**Files:**
- Create: `test-platform-v2/backend/tests/test_runtime_environment_profiles.py`
- Modify: `test-platform-v2/backend/tests/test_deploy_compose_contract.py`

- [x] **Step 1: Write profile contract tests**

Add tests that parse all three `*.env.example` files and assert:

```python
def test_runtime_profiles_have_unique_identity_and_storage() -> None:
    profiles = {name: read_profile(name) for name in ("local", "test", "production")}
    assert {profile["PLATFORM_TARGET"] for profile in profiles.values()} == {
        "local",
        "test",
        "production",
    }
    assert len({profile["COMPOSE_PROJECT_NAME"] for profile in profiles.values()}) == 3
    assert len({profile["FRONTEND_PORT"] for profile in profiles.values()}) == 3
    assert len({profile["DATABASE_URL"] for profile in profiles.values()}) == 3


def test_local_profile_is_development_only() -> None:
    profile = read_profile("local")
    assert profile["ENVIRONMENT"] == "development"
    assert profile["DATABASE_URL"].startswith("sqlite:///")
    assert profile["COOKIE_SECURE"] == "false"
    assert profile["PLATFORM_FRONTEND_URL"] == "http://localhost:5173"


def test_shared_profiles_are_production_like() -> None:
    for name in ("test", "production"):
        profile = read_profile(name)
        assert profile["ENVIRONMENT"] == "production"
        assert profile["DATABASE_URL"].startswith("postgresql://")
        assert profile["COOKIE_SECURE"] == "true"
        assert profile["PLATFORM_FRONTEND_URL"].startswith("https://")
```

- [x] **Step 2: Extend the Compose contract test**

Assert the Compose source contains no `container_name`, requires profile-provided `ENVIRONMENT`, `COOKIE_SECURE`, `DATABASE_URL`, and keeps `AUTO_CREATE_TABLES=false`.

- [x] **Step 3: Run the new tests and verify they fail**

Run:

```powershell
python -m pytest tests/test_runtime_environment_profiles.py tests/test_deploy_compose_contract.py -q
```

Expected: failure because runtime profile files do not exist and Compose still has fixed container names/hardcoded environment values.

### Task 2: Add three safe, fixed runtime profiles

**Files:**
- Create: `test-platform-v2/config/runtime/local.env.example`
- Create: `test-platform-v2/config/runtime/test.env.example`
- Create: `test-platform-v2/config/runtime/production.env.example`
- Modify: `test-platform-v2/backend/.env.example`
- Modify: `test-platform-v2/frontend/.env.example`

- [x] **Step 1: Add the local template**

Use fixed local values:

```dotenv
PLATFORM_TARGET=local
PLATFORM_FRONTEND_URL=http://localhost:5173
COMPOSE_PROJECT_NAME=cameltv-tp-local
FRONTEND_PORT=5173
BACKEND_PORT=8000
VITE_DEV_PORT=5173
VITE_PROXY_TARGET=http://127.0.0.1:8000
ENVIRONMENT=development
DATABASE_URL=sqlite:///./data/platform-local.db
AUTO_CREATE_TABLES=true
ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
CSRF_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
COOKIE_SECURE=false
AI_ENABLED=false
```

Keep `SECRET_KEY`, `ADMIN_PASSWORD`, and `TESTER_PASSWORD` empty in the committed example and require the ignored real profile to hold the generated values.

- [x] **Step 2: Add test and production templates**

Both shared profiles must use:

```dotenv
ENVIRONMENT=production
AUTO_CREATE_TABLES=false
COOKIE_SECURE=true
DATABASE_URL=postgresql://cameltv:change-me@postgres:5432/cameltv_test
```

Use distinct project names, frontend ports, database names, PostgreSQL passwords, and HTTPS origins. Production must use its own database name and origin; no value may point to the test database.

- [x] **Step 3: Document compatibility**

Update the existing backend/frontend examples to state that `.env` and `.env.local` remain supported for one-off worktrees, while long-lived environments use `config/runtime/<target>.env`.

- [x] **Step 4: Run profile tests**

Run:

```powershell
python -m pytest tests/test_runtime_environment_profiles.py -q
```

Expected: all profile contract tests pass.

### Task 3: Make Compose safe for simultaneous test and production stacks

**Files:**
- Modify: `test-platform-v2/deploy/docker-compose.yml`
- Modify: `test-platform-v2/backend/tests/test_deploy_compose_contract.py`

- [x] **Step 1: Remove fixed container names**

Delete the `container_name` keys for postgres, backend, and frontend so Docker Compose prefixes resources with `COMPOSE_PROJECT_NAME`.

- [x] **Step 2: Require profile security values**

Change backend environment entries to:

```yaml
- ENVIRONMENT=${ENVIRONMENT:?ENVIRONMENT is required}
- COOKIE_SECURE=${COOKIE_SECURE:?COOKIE_SECURE is required}
- DATABASE_URL=${DATABASE_URL:?DATABASE_URL is required}
- AUTO_CREATE_TABLES=false
```

Keep PostgreSQL credentials, volumes, health checks, non-root runtime, and Nginx same-origin proxy behavior unchanged.

- [x] **Step 3: Run Compose contract tests**

Run:

```powershell
python -m pytest tests/test_deploy_compose_contract.py -q
```

Expected: all Compose contract tests pass.

### Task 4: Add the environment launcher

**Files:**
- Create: `test-platform-v2/scripts/start-platform-environment.ps1`

- [x] **Step 1: Implement profile loading and validation**

The script accepts:

```powershell
param(
    [ValidateSet("local", "test", "production")]
    [string]$Target = "local",
    [ValidateSet("start", "status")]
    [string]$Action = "start",
    [switch]$ConfirmProduction
)
```

It resolves `config/runtime/$Target.env`, fails with a copy command when missing, parses non-comment `KEY=VALUE` entries without printing values, and validates:

- `PLATFORM_TARGET` equals the requested target.
- Ports are integers and distinct.
- local uses development + SQLite + insecure local cookie.
- test/production use production + PostgreSQL + secure cookie + HTTPS origin.
- production start requires `-ConfirmProduction`.

- [x] **Step 2: Implement idempotent local start**

For local:

- Reuse an existing listener only when its command line contains this worktree's backend/frontend path.
- Otherwise fail closed on occupied ports.
- Start Uvicorn and Vite hidden, with stdout/stderr in `%TEMP%\cameltv-platform-<target>`.
- Wait for backend `/health`, frontend `/login`, and proxied `/api/v1/open/health`.
- Write a secret-free runtime manifest with target, URLs, database backend/name, PIDs, and Git SHA.

- [x] **Step 3: Implement shared-environment start**

For test/production execute:

```powershell
docker compose `
  --project-name $profile.COMPOSE_PROJECT_NAME `
  --env-file $profilePath `
  -f "$platformRoot/deploy/docker-compose.yml" `
  up -d --build
```

Do not print the profile contents. `status` must use `docker compose ps` for shared environments and listener/health checks for local.

- [x] **Step 4: Create the ignored local runtime profile**

Copy `local.env.example` to `local.env`, generate independent strong values for `SECRET_KEY`, `ADMIN_PASSWORD`, and `TESTER_PASSWORD`, and keep the file ignored by Git.

- [x] **Step 5: Verify launcher behavior**

Run:

```powershell
pwsh scripts/start-platform-environment.ps1 -Target local -Action status
pwsh scripts/start-platform-environment.ps1 -Target local -Action start
```

Expected: both commands report `http://localhost:5173`, backend health 200, proxied health 200, and the fixed local SQLite database without exposing credentials.

### Task 5: Document the operating model and Batch 56 carry-over

**Files:**
- Modify: `test-platform-v2/README.md`
- Modify: `test-platform-v2/deploy/README.md`
- Create: `test-platform-v2/work-logs/batch-57-environment-targets-and-batch56-acceptance.md`

- [x] **Step 1: Document fixed-address behavior**

Add a concise table:

| Target | Access | Database | Startup |
| --- | --- | --- | --- |
| local | `http://localhost:5173` | dedicated local SQLite | launcher |
| test | profile HTTPS URL | dedicated test PostgreSQL | Compose project |
| production | profile HTTPS URL | dedicated production PostgreSQL | explicit confirmed Compose project |

State that the browser address selects the platform instance; users never switch the platform database from the page.

- [x] **Step 2: Distinguish `/environment`**

Document that `/environment` manages the tested system's target URLs/variables and does not change the test platform's own database.

- [x] **Step 3: Record Batch 56 residuals**

Record the authoritative `NEEDS WORK` verdict and the ten formal blockers:

- P0: test node 6 returns 503; six-service OpenAPI incomplete; invalid Bearer accepted; admin login does not establish a session; real AI/OCR unavailable; old PostgreSQL snapshot missing; design-source evidence pack not reproducible.
- P1: device agent/SoloX unavailable; ELK read-only trace evidence missing; production browser timeout/insufficient content.

Also record the evidence inconsistency: missing standalone issue register/Leader Verdict/C-CONDITIONS update, and Knowledge/Wiki stubs conflicting with the claimed closure of `G56-011`.

### Task 6: Run required verification

**Files:**
- Update: `test-platform-v2/work-logs/batch-57-environment-targets-and-batch56-acceptance.md`

- [x] **Step 1: Backend hard gate and targeted tests**

Run:

```powershell
python -m ruff check app/ --select F821
python -m pytest tests/test_runtime_environment_profiles.py tests/test_deploy_compose_contract.py -q
```

Expected: zero F821 errors and all targeted tests pass.

- [x] **Step 2: Frontend hard gates**

Run:

```powershell
npm run typecheck
npm run build
npm test
```

Expected: all commands exit 0; record the exact test count and any unchanged dependency advisory.

- [x] **Step 3: Browser verification**

Detect localhost servers first, then verify visible-browser login page load, title, no console errors, no failed requests, and one successful proxied health request at `http://localhost:5173`.

- [x] **Step 4: Worktree and secret scan**

Run:

```powershell
pwsh scripts/git/verify-ai-worktree.ps1 -RequireMetadata -ExpectedWorkflow agent-team -ExpectedExecutor codex
git status --short
```

Confirm no `.env`, database, credentials, logs, node_modules, or runtime manifests are tracked.

- [x] **Step 5: Commit locally**

Stage only the Batch 57 files and commit:

```powershell
git commit -m "feat: add fixed runtime environment profiles"
```

Do not push. Before every push, present the AGENTS.md change summary and ask the exact Batch 48+ confirmation question.

## Self-review

- Spec coverage: fixed local/test/production addresses, separate databases, no repeated manual switching, local 5173 deployment, and Batch 56 residual review are all mapped to tasks.
- Placeholder scan: committed examples intentionally use `change-me` only for secret fields; no implementation step is deferred.
- Type/name consistency: `PLATFORM_TARGET`, `PLATFORM_FRONTEND_URL`, `COMPOSE_PROJECT_NAME`, `FRONTEND_PORT`, `BACKEND_PORT`, `ENVIRONMENT`, and `DATABASE_URL` use identical names across profiles, launcher, tests, and docs.
