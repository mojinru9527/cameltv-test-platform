# Batch 230 Acceptance Evidence

> Date: 2026-09-05 | Branch: `feature/batch-230-prod-retest-defects` | Local browser: `http://127.0.0.1:5231`

All screenshots in this directory were produced during the new Batch 230 run. No credential, API key, cookie, or plain token is stored here. The local account email shown in the sidebar footer was redacted; the generic `admin` audit actor remains visible only where required to prove S6.

| Evidence ID | File | Coverage | Type | Result | Reuse rule |
|-------------|------|----------|------|--------|------------|
| E230-01 | `qa-02-version-task-list-persisted.png` | Version task list persistence | Screenshot | PASS | Reuse until version-task list changes |
| E230-02 | `qa-03-version-task-blocked-visible.png` | Blocked run reason and status | Screenshot | PASS | Reuse until run result UI/service changes |
| E230-03 | `qa-04-ai-discover-error-visible.png` | Empty-key model discovery error | Screenshot | PASS | Reuse until AI config discovery changes |
| E230-04 | `qa-05-defect-id-prefix-search.png` | Defect full ID/prefix search | Screenshot | PASS | Reuse until defect filters change |
| E230-05 | `qa-06-contract-snapshot-rendered.png` | Snapshot content plus pre-fix toast overlap | Before-fix screenshot | FAIL evidence | Do not use as PASS evidence |
| E230-06 | `qa-07-scope-audit-operator.png` | Pre-fix nickname inconsistency | Before-fix screenshot | FAIL evidence | Do not use as PASS evidence |
| E230-07 | `qa-08-contract-empty-desktop-1440x900.png` | Contract empty state, desktop | Screenshot | PASS | Reuse until Contract page/client changes |
| E230-08 | `qa-09-scope-audit-login-username.png` | Analyze/review actor is `admin` | Screenshot | PASS | Reuse until Scope audit changes |
| E230-09 | `qa-10-contract-empty-tablet-768x1024.png` | Contract empty state, tablet | Screenshot | PASS | Reuse until responsive layout changes |
| E230-10 | `qa-11-contract-empty-mobile-390x844.png` | Contract empty state, mobile | Screenshot | PASS | Reuse until responsive layout changes |
| E230-11 | `s5-search-by-defect-id.png` | Earlier S5 full-ID browser proof | Screenshot | PASS | Superseded by E230-04 for final QA |
| E230-12 | `s7-defect-banner-shown.png` | Valid `/defect` legacy banner | Screenshot | PASS | Reuse until legacy banner/router changes |
| E230-13 | `s7-defects-404-no-banner.png` | `/defects` clean 404 boundary | Screenshot | PASS | Reuse until legacy banner/router changes |
| E230-14 | `_snapshot-defect-list.txt` | Browser-visible defect snapshot | Text snapshot | SUPPORTING | Not a substitute for screenshots/tests |

## Browser Facts

- Mission 2 was created through the frontend wizard.
- Its manual source was attached through the Source dialog, then Scope analysis and approval were executed through visible buttons.
- `GET /api/v2/missions/2/contract` returned HTTP 200 after the fix.
- Contract empty state: visible, no toast, console 0 errors / 0 warnings.
- Mobile geometry: viewport 390x844, document `scrollWidth=390`, `clientWidth=390`.
- Audit page: `scope:analyze` and `scope:review` both show operator `admin`.

The invalid login-transition screenshot and the backend-restart redirect screenshot were removed before evidence commit.
