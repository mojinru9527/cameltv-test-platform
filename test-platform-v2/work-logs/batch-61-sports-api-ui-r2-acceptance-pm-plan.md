# Batch 61 Sports API/UI R2 Acceptance - PM Plan

> **PM** | Date: 2026-08-01 | Status: In progress

## Specification summary

**Source:** `batch-61-sports-api-ui-r2-acceptance-prd-summary.md` and Batch 61 implementation plan Tasks 6-9.

**Delivery rule:** Locally controllable hardening must complete in W2. External Test5 work remains `BLOCKED` until its prerequisite package is complete; it must never be simulated as passing.

## Development tasks

### Task 1: Freeze baseline and false-green regressions

**Acceptance criteria**

- Record clean SHA, worktree metadata, ports, dependency audit counts, typecheck, security-test, and Playwright collection results.
- Tests prove that missing environment, authorization, credentials, API assets, or business fixtures cannot produce `PASS`.

**Files**

- `tests/automation/ui/tests/security/no-false-green.spec.ts`
- `test-platform-v2/backend/tests/playwright/specs/production-smoke.spec.ts`
- `test-platform-v2/backend/tests/playwright/specs/production-web-smoke.spec.ts`

### Task 2: Implement structured preconditions and stable data contracts

**Acceptance criteria**

- No default sports target URL.
- Structured `BLOCKED` includes missing key and owner and is raised before browser/network activity.
- Test data uses configured business keys; write journeys require a disposable identity, explicit authorization, amount/rate limits, and cleanup owner.
- Production rejects every method except GET/HEAD.

**Files**

- `tests/automation/ui/utils/preconditions.ts`
- `tests/automation/ui/utils/test-data.ts`
- `tests/automation/ui/playwright.config.ts`
- `tests/automation/ui/tests/security/security-utils.spec.ts`

### Task 3: Harden sports user/admin journeys

**Acceptance criteria**

- Home, list, detail, auth/entitlement, recharge, refund, and bonus journeys have explicit business assertions.
- Missing R2 data is structured `BLOCKED`, not an unexplained skip.
- Minimal content/order admin reconciliation is read-only.
- Credentials and raw sensitive traffic never enter AI prompts or committed evidence.

**Files**

- `tests/automation/ui/utils/auth.ts`
- `tests/automation/ui/utils/traffic-capture.ts`
- `tests/automation/ui/utils/ai-test.ts`
- `tests/automation/ui/tests/{home,list,detail,pay,refund,bonus,admin}/**`

### Task 4: Upgrade and audit the sports automation supply chain

**Acceptance criteria**

- Upgrade `@midscene/web` from 0.20.x to a supported 1.x release with a committed lockfile.
- `npm ci`, `npm audit --omit=dev`, typecheck, security tests, and test collection pass.
- Production dependency audit reports zero high/critical findings.
- Backend `pip-audit` uses an exact tool version; raw JSON remains outside Git and only a sanitized summary enters QA evidence.

**Files**

- `tests/automation/ui/package.json`
- `tests/automation/ui/package-lock.json`
- `tests/automation/ui/utils/ai-test.ts`

### Task 5: Build API acceptance assets and executable preflight

**Acceptance criteria**

- Feature points map to positive and negative cases with parameter, business, and response assertions.
- The runner validates VPN window, six current contract hashes, account scope, stable data keys, rate/cleanup policy, and code SHAs without external state changes.
- Production is mechanically GET/HEAD only; missing prerequisites produce `BLOCKED`.
- Authorized execution records platform UI/API/DB/audit agreement; without authorization the result document remains honest.

**Files**

- `tests/test-cases/batch-61-sports-api-cases.md`
- `tests/automation/api/batch61/**`
- `test-platform-v2/work-logs/batch-61-sports-api-results.md`
- `test-platform-v2/work-logs/evidence/batch-61-sports-platform-validation/api/**`

### Task 6: Build UI R2 acceptance assets and evidence index

**Acceptance criteria**

- Feature points map to at least one positive and one negative case.
- Read-only critical journeys, browser quality, and PC evidence requirements are explicit.
- Write journeys remain separately `BLOCKED` without written authorization and cleanup ownership.
- Result totals derive from case rows, not screenshot counts.

**Files**

- `tests/test-cases/batch-61-sports-ui-cases.md`
- `test-platform-v2/work-logs/batch-61-sports-ui-results.md`
- `test-platform-v2/work-logs/evidence/batch-61-sports-platform-validation/{ui,pc-usage-snapshots}/**`

### Task 7: QA reconciliation and delivery

**Acceptance criteria**

- Run affected tests plus repository-required backend/frontend full gates.
- Update Batch 61 issue register, acceptance matrix, readiness, evidence indexes, and W2 QA report with exact totals.
- Draft PR remains `NEEDS WORK` if any locally controllable P0/P1 item fails or is not run.
- No push occurs without the mandatory per-push user confirmation.

## Risks

| Risk | Control |
| --- | --- |
| Test5 prerequisites remain unavailable | Complete local hardening and preserve structured external `BLOCKED` |
| Midscene 1.x API incompatibility | Isolated dependency slice, typecheck/security/collection before journey changes |
| Generated reports leak secrets or enter Git | Store raw reports outside source; scan and commit sanitized summaries only |
| Production mutation | Fail-closed request method policy and no production write execution |
