# Batch 61 Sports API/UI R2 Acceptance - PRD Summary

> **Product** | Date: 2026-08-01 | Status: Approved for implementation

## 1. Problem statement

Batch 60 proved that the sports automation can be collected, but it cannot yet support a production-readiness verdict. Missing credentials can be skipped, missing business data can silently skip journeys, production smoke assertions can pass without a working login or API asset, and the sports automation runtime currently contains seven high-severity dependency findings.

Users need a result that distinguishes verified behavior from missing external prerequisites. A green run must mean that the expected business outcome was observed; it must not mean only that a page opened or a script finished.

## 2. Success metrics

| Metric | Baseline | Batch 61 W2 target | Measurement |
| --- | ---: | ---: | --- |
| Unaccepted high/critical production dependency findings in `tests/automation/ui` | 7 high / 0 critical | 0 | `npm audit --omit=dev` after clean install |
| Unexplained runtime skips in sports P0/P1 journeys | 7 known data-dependent skips | 0 | Playwright collection and controlled precondition tests |
| Missing prerequisites reported before browser/network activity | Inconsistent | 100% | False-green and precondition contract tests |
| Collected P0/P1 journeys with explicit business oracle | Partial | 100% or structured external `BLOCKED` | DOM/API/data assertion review and execution matrix |
| Production methods | Not mechanically restricted across every suite | GET/HEAD only | Preflight and request-policy tests |

## 3. Scope

- Harden sports Playwright environment, authorization, data, and evidence preconditions.
- Add deterministic data keys and a minimal operations-admin read-only journey.
- Make production smoke fail or block when credentials, login, API assets, or business fixtures are unavailable.
- Upgrade `@midscene/web` to an audited supported 1.x version and rerun security, type, collection, and dependency gates.
- Produce API and UI feature-point matrices with positive/negative cases and honest execution results.
- Execute locally controllable negative/preflight tests; execute Test5 R2 only after every required external input is authorized and available.

## 4. Non-goals

- No Test5 VPN switch, account use, or external request without a documented authorization window.
- No payment, refund, bonus, publish, ban, stream, delete, transfer, or other production write.
- No fabricated screenshot, Mock success, or historical Batch 60 evidence promoted to Batch 61 `PASS`.
- No testing-platform product UI work and no W3 release-control implementation.
- Open conditions unrelated to sports acceptance, including G56-011/G56-012 and platform-wide legacy workflows, remain outside this W2 branch.

## 5. User stories and acceptance

### US-1 Trustworthy blocked results

As an acceptance reviewer, I want missing environment, authorization, credentials, contracts, or stable data to produce a structured `BLOCKED` result, so that an incomplete run cannot be mistaken for a pass.

Acceptance: Given any required input is missing, when the suite starts, then it identifies the missing key and owner before opening a browser or sending a request.

### US-2 Business-level assertions

As a sports product owner, I want every P0/P1 journey to verify a visible result and the relevant API/data fact, so that a green result proves business behavior.

Acceptance: Given an authorized stable record, when a journey runs, then DOM, API, evidence-redaction, and applicable data/admin reconciliation assertions agree.

### US-3 Safe production observation

As a production owner, I want production automation restricted to approved read-only observation, so that acceptance work cannot mutate production.

Acceptance: Given a production target, when a request method is not GET or HEAD, then preflight rejects it before network activity.

### US-4 Auditable automation supply chain

As a security reviewer, I want the sports automation runtime free of unaccepted high/critical findings, so that test evidence is not produced by a known high-risk dependency chain.

Acceptance: Given a clean install from the committed lockfile, when the production dependency audit runs, then high and critical totals are zero and the security regression suite passes.

## 6. Open conditions and external blockers

| Source | W2 treatment |
| --- | --- |
| C31-3 operations acceptance address/read-only account | Partially addressed by read-only admin case design; remains `BLOCKED` until an authorized account and address are supplied |
| C55-5-P2 responsive matrix | Applied to authorized sports UI journeys only; platform-wide closure is not claimed |
| B60-BLK-001 Test5/VPN/contracts/accounts/data | Remains external `BLOCKED`; owner is `UNASSIGNED` |
| B60-P0-001/P0-002/P1-012/P1-013/P1-023 | W2 release scope |

## 7. Release policy

The maximum result without the R2 prerequisite package is `LOCAL HARDENING COMPLETE / EXTERNAL BLOCKED`. W2 cannot report Test5 or production business journeys as `PASS` until current contracts, authorization, credentials, stable keys, and evidence are available.
