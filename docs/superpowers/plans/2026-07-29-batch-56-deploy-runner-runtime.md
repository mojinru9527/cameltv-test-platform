# Batch 56 Deploy Runner Runtime Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the deployed backend image capable of running the bundled UI Playwright tests, importing the pinned root `lanhu-mcp` module, and performing ffprobe-based media checks.

**Architecture:** Build the backend from the repository root so one Docker context contains both `test-platform-v2/backend/tests/playwright` and the root `lanhu-mcp` submodule. Keep Python as the application base, install Node/npm and ffmpeg in the runtime image, install the npm-locked Playwright dependencies with `npm ci`, align Python Playwright to that lock version, and install one shared Chromium runtime.

**Tech Stack:** Docker BuildKit, Docker Compose, Python 3.12, Node.js/npm, Playwright Chromium, ffmpeg, Pytest.

---

### Task 1: Lock the deploy contract

**Files:**
- Modify: `test-platform-v2/backend/tests/test_deploy_compose_contract.py`

- [ ] Add assertions that the Compose backend build context is the repository root and the Dockerfile remains `test-platform-v2/backend/Dockerfile`.
- [ ] Add assertions that the Dockerfile copies the Playwright lock/package files before `npm ci`, copies the bundled specs, copies `lanhu-mcp`, installs Node/npm/ffmpeg, and installs Chromium for the aligned Python/Node Playwright version.
- [ ] Add assertions that the root `.dockerignore` excludes dependency, test-result, VCS, and local worktree metadata.
- [ ] Run `python -m pytest tests/test_deploy_compose_contract.py -q` from `test-platform-v2/backend`; the new assertions must fail before implementation.

### Task 2: Implement the runtime image

**Files:**
- Modify: `.dockerignore`
- Modify: `test-platform-v2/backend/Dockerfile`
- Modify: `test-platform-v2/deploy/docker-compose.yml`

- [ ] Change only the backend Compose build context/path and add non-secret runtime path variables; preserve required secrets, production-ingest opt-in, PostgreSQL dependency, and `tp-artifacts`.
- [ ] Add root-context copy paths to the backend Dockerfile.
- [ ] Install Node/npm, ffmpeg, npm-locked Playwright packages, an aligned Python Playwright package, and shared Chromium.
- [ ] Keep OCR engines, ADB and SoloX out of scope and do not add mock-success claims.
- [ ] Run the focused Pytest contract until it passes.

### Task 3: Document capability and limits

**Files:**
- Modify: `test-platform-v2/deploy/README.md`
- Modify: `test-platform-v2/deploy/CLAUDE.md`

- [ ] Document the root build-context/submodule precondition, reproducible `npm ci`, runtime probes, persistent artifacts, and larger image footprint.
- [ ] State explicitly that generic OCR command providers, ADB/device access, and SoloX remain separately provisioned and are not solved by this image.
- [ ] Document `docker compose build --check backend` and runtime probe commands without claiming a full image build was executed.

### Task 4: Verify without an unbounded image build

**Files:**
- Verify only; no additional files.

- [ ] Run focused Pytest and `git diff --check`.
- [ ] Run `docker compose config --quiet` with non-secret temporary environment values.
- [ ] Run Docker build check if supported; do not wait for a full Chromium image build if dependency download is excessive.
- [ ] Inspect the final diff to confirm existing Compose security defaults and `tp-artifacts` changes remain.

### Task 5: Drop backend runtime root privileges

**Files:**
- Modify: `test-platform-v2/backend/Dockerfile`
- Modify: `test-platform-v2/backend/tests/test_deploy_compose_contract.py`
- Modify: `test-platform-v2/deploy/README.md`
- Modify: `test-platform-v2/deploy/CLAUDE.md`

- [ ] Add a failing contract that requires a Python virtual environment at `/opt/venv`, rejects `/root/.local`, and requires a fixed non-root runtime user.
- [ ] Require `/app`, `/data`, `/ms-playwright`, `/app/storage`, and the runtime home/cache locations to be readable/writable by that user before the final `USER` instruction.
- [ ] Move builder and runtime Python installs into `/opt/venv`, retain npm-locked Playwright, Chromium, ffmpeg, and the copied Lanhu module, then switch to `cameltv:cameltv`.
- [ ] Document the fixed UID/GID, named-volume ownership behavior, one-time ownership repair for pre-existing volumes, and the non-root runtime probes.
- [ ] Run focused Pytest, Ruff, Compose config, standalone Docker build check, and Compose build check; do not perform the full image build.
