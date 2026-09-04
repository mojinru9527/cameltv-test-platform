# Batch 229 - QA Report

> QA | Date: 2026-09-04 | Verdict: PASS (local code and browser chain)

## Test Summary

| Area | Result |
|------|--------|
| Backend | 2425 passed / 49 skipped / 1 xfailed / 0 failed; focused 67 passed |
| Frontend | 140 files / 629 tests; typecheck, lint and build all passed |
| Architecture gates | app import, Ruff F821, Alembic 8 tests and route guards 4 tests passed |
| Repository gates | C audit 0/0; common-bug scan 0 HARD; dev-gate PASS_WITH_WARN |
| Browser | 7 safe screenshots; 0 console errors; creation/disable/delete each exactly 1 write request |

Full commands and counts: `work-logs/evidence/batch-229-worker-token-onboarding/regression/test-results.md`.

## Acceptance Matrix

| Condition | Result | Evidence |
|-----------|--------|----------|
| Worker heartbeat accepts only `workers:register` API Token | PASS | `workflows.py:33-38`, `service.py:79-87`; E229-01 |
| Wrong scope is 403; disabled Token is 401 | PASS | `test_worker_token_auth.py`; 3 integration tests |
| Successful heartbeat updates Token usage | PASS | `token_service.py:43-51`; database assertion |
| Runtime provides an admin creation entry | PASS | `runtime/index.tsx:42/144-152`; three viewports |
| Read-only user receives contact-admin guidance only | PASS | Runtime focused test |
| System deep link selects API Token and Worker purpose | PASS | `system/index.tsx:43-59`, `TokensTab.tsx:73-82`; browser |
| Purpose maps to minimum scope | PASS | `tokenPurposes.ts`; focused tests and browser request |
| Setup is directly executable in Bash | PASS | generated lines use `export`; browser boolean checks |
| Plain Token is one-time and not persisted in evidence | PASS | success dialog closed in one operation; temporary snapshots removed |
| Stop/delete revokes through visible controls | PASS | one PUT + one DELETE, both 200, final empty state |
| Empty Token stops before child processes | PARTIAL | launcher contract test passed; Bash/Docker unavailable locally |
| System tabs and global header fit 390/768/1440 | PASS | final box metrics + 7 screenshots |

## Code Logic And Anti-Fake-Success Audit

- Heartbeat uses the existing SHA-256 Token lookup and rate limiter, then enforces `workers:register`; it does not accept browser Cookie fallback.
- Wrong-scope, disabled and successful cases execute through FastAPI, SQLite and the real Token creation route. The successful test reloads the ORM row and asserts `last_used_at`.
- Browser tests used real login, menus, Vite proxy and FastAPI persistence. No frontend route or response was mocked.
- The created local Token was disabled and deleted through visible UI controls. Only safe boolean/count results were recorded.
- Local tests do not prove a production Worker, Temporal cluster or Test5 runner is online.

## Defects

| ID | Severity | Description | Status |
|----|----------|-------------|--------|
| B229-P1-01 | P1 | Heartbeat accepted browser JWT but not a dedicated machine Token | Fixed |
| B229-P1-02 | P1 | Token UI generated only CI scope, so Worker could not register | Fixed |
| B229-P1-03 | P1 | Runtime had no discoverable credential path for black-box admins | Fixed |
| B229-P1-04 | P1 | Empty Token launched children into a repeated 401 loop | Fixed |
| B229-P1-05 | P1 | Copied setup used unexported shell variables, so the child script still saw an empty Token | Found in QA and fixed |
| B229-P2-01 | P2 | System tabs clipped/overlapped at 390 and 768 widths | Found in browser QA and fixed |
| B229-P2-02 | P2 | Global header project name overlapped action controls at 768 width | Found in browser QA and fixed |

## Remaining Boundary

- Linux launcher execution is not available on this Windows host. Contract tests cover ordering, but a release environment must perform the real process start.
- C227-2 remains Deferred: production sports AI acceptance still needs the external AI/OpenAPI/Test5/Worker conditions and must not be inferred from this local batch.
- No production deployment occurred.

## Release Recommendation

READY FOR DRAFT PR after the repository-mandated one-time confirmation. Required checks and final `audit-ai-pr.ps1 -RequireSuccessfulChecks` must pass before Leader approval and squash merge.

## Retro Card

| Planned vs actual | Defects (P0/P1/P2/P3) | Rework | Root cause | Next prevention |
|-------------------|-------------------------|--------|------------|-----------------|
| 4.5h / about 3.5h | 0/5/2/0 | 3 | Technical debt + missing executable/browser contract | Worker onboarding QA must execute copied configuration semantics and inspect 390/768/1440 pixel boxes before PR |

**Skills used**: cameltv-agent-team, cameltv-bug-guard, cameltv-ui-conventions, Playwright CLI.
