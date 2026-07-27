# API Test OpenVPN Auto-Connect Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Before an API request targets a configured test environment, automatically connect the backend host's OpenVPN profile and stop the request with a clear error if the VPN cannot become reachable.

**Architecture:** Add one backend VPN preflight service and call it from the shared API execution path so quick debug, saved-case execution, dataset runs, and background tasks behave consistently. The service probes the target host first, starts OpenVPN Connect's latest profile only when needed, waits for reachability, and never stores VPN profiles or credentials in Git. The API-case screen will select Test 5 by default and pass its environment ID so the backend can identify the request as a test-environment call.

**Tech Stack:** FastAPI, SQLAlchemy, Python `socket`/`subprocess`, Pydantic settings, React 18, TypeScript, Vitest, pytest

**Status:** Complete — backend, frontend, regression, build, and browser acceptance verified on 2026-07-17.

---

### Task 1: Specify VPN preflight behavior

**Files:**
- Create: `backend/tests/test_openvpn_service.py`
- Modify: `backend/tests/test_api_execution_snapshots.py`

- [ ] **Step 1: Write failing service tests**

Cover these exact outcomes:

```python
def test_non_test_environment_does_not_start_openvpn(): ...
def test_reachable_test_target_reuses_current_vpn_connection(): ...
def test_unreachable_test_target_starts_openvpn_connect_and_waits(): ...
def test_request_is_blocked_when_openvpn_cannot_connect(): ...
```

- [ ] **Step 2: Write a failing execution integration test**

Patch the VPN preflight to raise `VpnConnectionError`, call `_do_execute`, and assert that no `httpx.Client.request` call occurs and the returned error explains that OpenVPN failed to connect.

- [ ] **Step 3: Run the focused tests**

Run: `.venv/Scripts/python.exe -m pytest tests/test_openvpn_service.py tests/test_api_execution_snapshots.py -q`

Expected: FAIL because the VPN service and execution hook do not exist yet.

### Task 2: Implement safe OpenVPN Connect startup

**Files:**
- Create: `backend/app/services/openvpn_service.py`
- Modify: `backend/app/core/config.py`
- Modify: `backend/.env.example`
- Modify locally (ignored): `backend/.env`

- [ ] **Step 1: Add explicit settings**

Add settings equivalent to:

```python
openvpn_auto_connect_enabled: bool = False
openvpn_connect_executable: str = "C:/Program Files/OpenVPN Connect/OpenVPNConnect.exe"
openvpn_connect_timeout_seconds: float = 30.0
openvpn_probe_timeout_seconds: float = 1.0
```

Document the same variables in `.env.example`; enable the feature only in the ignored local `.env`. Do not add an `.ovpn` path, password, username, certificate, or profile contents.

- [ ] **Step 2: Implement reachability-first auto-connect**

`ensure_vpn_for_test_environment(db, environment_id, target_url)` must:

1. Return `not_required` if no selected environment, the environment is not `test`, or auto-connect is disabled.
2. Probe the resolved URL host and its effective port; return `connected` without touching OpenVPN when already reachable.
3. Serialize concurrent connection attempts with a process lock.
4. Run OpenVPN Connect argument arrays without `shell=True`: set `launch-options=connect-latest`, quit the disconnected app, then relaunch it minimized.
5. Probe until the configured timeout and raise `VpnConnectionError` if the executable is missing, startup fails, or the target remains unreachable.

- [ ] **Step 3: Run service tests**

Run: `.venv/Scripts/python.exe -m pytest tests/test_openvpn_service.py -q`

Expected: PASS.

### Task 3: Put VPN before every API request

**Files:**
- Modify: `backend/app/services/api_execution_service.py`
- Test: `backend/tests/test_api_execution_snapshots.py`

- [ ] **Step 1: Call the VPN preflight after URL resolution and before the request snapshot/HTTP client**

```python
try:
    vpn = ensure_vpn_for_test_environment(db, environment_id, resolved_url)
except VpnConnectionError as exc:
    return _error_result(str(exc), request_snapshot)
```

Build enough of the request snapshot before returning so the user can still see which request was blocked. Include the non-sensitive VPN status in successful execution results.

- [ ] **Step 2: Verify no request escapes on VPN failure**

Run: `.venv/Scripts/python.exe -m pytest tests/test_api_execution_snapshots.py -q`

Expected: PASS, including the assertion that the HTTP client was not called.

### Task 4: Select Test 5 for saved API cases and expose status

**Files:**
- Modify: `frontend/src/pages/apitest/components/ApiCaseTab.tsx`
- Modify: `frontend/src/pages/apitest/components/ApiCaseTab.test.tsx`
- Modify: `frontend/src/pages/apitest/components/DebugTab.tsx`
- Modify: `frontend/src/types/index.ts`

- [ ] **Step 1: Write failing component tests**

Mock environments with Test 5 plus another environment. Assert Test 5 is selected by default, its ID is passed to single execution and task creation, and an execution error displays the VPN-specific message.

- [ ] **Step 2: Add the environment selector and feedback**

Reuse the existing environment API and Select components. Keep Test 5 as the default; pass `environment_id` to `executeApiCase` and `createApiExecutionTask`. Show a compact “发送时自动连接 OpenVPN” hint for `test` environments and render the returned VPN status near the response result.

- [ ] **Step 3: Run the focused frontend tests**

Run: `npm test -- --run src/pages/apitest`

Expected: PASS.

### Task 5: Regression and acceptance verification

**Files:**
- Modify this plan's checkboxes/status only after verification.

- [ ] **Step 1: Run backend API-test regression tests**

Run: `.venv/Scripts/python.exe -m pytest tests/test_openvpn_service.py tests/test_api_execution_snapshots.py tests/test_apitest_generation.py tests/test_apitest_assets.py tests/test_apitest_tasks.py tests/test_apitest_project_isolation.py -q`

Expected: PASS.

- [ ] **Step 2: Build the frontend**

Run: `npm run build`

Expected: PASS.

- [ ] **Step 3: Browser acceptance**

Open the API-case module with mocked API data and verify Test 5 is selected by default, the OpenVPN hint is visible, a single-case execution submits Test 5's environment ID, and the VPN result/error appears in the response area.
