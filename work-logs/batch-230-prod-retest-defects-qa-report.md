# Batch 230 - QA Report

> QA | Date: 2026-09-05 | Verdict: PASS (local code, real browser, and repository gates)

## Test Summary

| Area | Result |
|------|--------|
| Backend | 2444 passed / 49 skipped / 1 xfailed / 0 failed; focused 16 passed |
| Frontend | 146 files / 664 tests passed; focused 12 passed |
| Build and static checks | Typecheck, full lint, production build, app import, Ruff F821 all passed |
| Migration and architecture | Alembic single-head/revision 8 passed; route guards 4 passed |
| Repository gates | C audit 0 errors / 0 warnings; common-bug scan 0 HARD / 330 historical WARN |
| Browser | Real UI workflow passed; HTTP 200 contract empty state; 0 console errors/warnings; 390/768/1440 screenshots |

This report uses only Batch 230's newly executed tests and browser evidence. It does not use an older report as proof of PASS.

## Executed Gates

| Command | Exit | Result |
|---------|-----:|--------|
| `python -m pytest tests/test_aitde_scope_service.py tests/test_aitde_contract_service.py -q` | 0 | 16 passed |
| `python -m pytest -q` | 0 | 2444 passed, 49 skipped, 1 xfailed |
| `npx vitest run --maxWorkers=3` | 0 | 146 files, 664 tests passed |
| `npm run typecheck` | 0 | Passed |
| `npm run lint` | 0 | Passed with zero warnings |
| `npm run build` | 0 | Production build completed |
| `python -m ruff check app --select F821` | 0 | All checks passed |
| `python -c "import app.main"` | 0 | App import passed |
| Migration single-head + revision tests | 0 | 8 passed |
| `pwsh scripts/git/dev-gate.ps1 ...` | 1 | `PASS_WITH_WARN`; G0-G2 passed, 0 HARD / 330 existing WARN |
| `pwsh scripts/git/audit-cconditions.ps1` | 0 | 0 errors / 0 warnings |

## Acceptance Matrix

| Slice | Result | Evidence |
|-------|--------|----------|
| S1 Contract snapshot is readable and empty snapshot cannot freeze | PASS | `qa-06-contract-snapshot-rendered.png`; backend/frontend contract tests |
| S2 Version task list is reachable and persistent | PASS | `qa-02-version-task-list-persisted.png`; list/navigation tests |
| S3 One-click run exposes blocked reason rather than 0/0 success | PASS | `qa-03-version-task-blocked-visible.png`; version-task tests |
| S4 AI model discovery does not report false success | PASS | `qa-04-ai-discover-error-visible.png`; AI config tests |
| S5 Defect search accepts full ID and prefix without breaking project isolation | PASS | `qa-05-defect-id-prefix-search.png`; 4 backend isolation tests |
| S6 Scope audit records the stable login username | PASS | `qa-09-scope-audit-login-username.png`; analyze/review rows both show `admin` |
| S7 Ambiguity spelling and 404 banner boundary are correct | PASS | `s7-defect-banner-shown.png`, `s7-defects-404-no-banner.png`; 5 frontend tests |

## QA Rework Findings

| ID | Severity | Finding | Resolution | Status |
|----|----------|---------|------------|--------|
| B230-QA-01 | P2 | Scope audit used nickname (`超级管理员`) while defect audit used login name (`admin`) | `_audit` now records `User.username`; tests cover nickname-present and fallback cases | Fixed in `a1d5a780` |
| B230-QA-02 | P2 | First visit to an ungenerated Contract returned HTTP 404, produced console noise and a red toast | Kept business code 404 but changed transport status to HTTP 200; endpoint test locks the envelope | Fixed in `a1d5a780` |
| B230-QA-03 | P3 | Direct Mission navigation surfaced Axios cancellation as a literal `canceled` toast | AITDE v2 interceptor now rejects cancellations silently while retaining ordinary error toasts | Fixed in `0c169c29` |

`qa-06` and `qa-07` intentionally remain as before-fix evidence. `qa-08`, `qa-09`, `qa-10`, and `qa-11` are the corresponding after-fix evidence.

## Browser Verification

- Used the visible local frontend at `http://127.0.0.1:5231`; no API was used to create Mission 2, attach its source, analyze/review Scope, or open the audit page.
- Contract request for Mission 2 returned HTTP 200 with business code 404, rendered `尚未生成 Test Contract。`, produced no toast, and left the console at 0 errors / 0 warnings.
- Scope analysis and approval created `scope:analyze` and `scope:review` audit rows whose operator is `admin`.
- Direct navigation after the cancellation fix produced `toasts=[]`; the mobile page had `scrollWidth=clientWidth=390`.
- Desktop 1440x900, tablet 768x1024, and mobile 390x844 screenshots show the empty state without overlap or horizontal overflow.

## Logic and Anti-Fake-Success Audit

- Empty Contract is distinguished from a real backend failure: only business/HTTP 404 maps to `null`; other failures still reach the page ErrorState.
- The HTTP 200 + business 404 behavior is verified through FastAPI TestClient, not by mocking the router.
- Cancellation remains a rejected Promise, so query lifecycle semantics are preserved; only the inappropriate user toast is suppressed.
- Defect search keeps `project_id`, severity, status, and assignee filters outside the title/ID `or_`, preserving tenant isolation.
- Version task blocked counts remain arithmetically valid; the synthetic plan failure explains the block without inventing `blocked > total`.

## Remaining Boundary

- No production deployment occurred in this batch; this is code and local browser acceptance only.
- Historical audit rows are not backfilled and can retain older nickname/blank values.
- `production_operation:allowed` and `apitest:execute_prod` still do not receive operator identity. This is tracked as `C230-1` for a dedicated batch.
- The 330 common-bug warnings are the repository baseline; this batch introduces no HARD finding.

## Release Recommendation

READY FOR DRAFT PR after the repository-mandated one-time confirmation. Required checks and final `audit-ai-pr.ps1 -RequireSuccessfulChecks` must pass before Leader approval and squash merge.

## 复盘卡

| Planned vs actual | Defects (P0/P1/P2/P3) | Rework | Root cause | Next prevention |
|-------------------|-------------------------|--------|------------|-----------------|
| 9.5h / actual not reliably measured across executor handoff | 0/3/5/3 (including QA findings; one report withdrawn) | 2 QA correction rounds | Contract convention drift + audit naming drift + missing cancellation guard | Every expected empty state must assert transport status, toast list, console errors, and actor naming in one browser pass |

**Skills used**: cameltv-agent-team, cameltv-bug-guard, cameltv-ui-conventions, Playwright CLI.
