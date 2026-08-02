# Batch 61 Sports API/UI R2 Acceptance QA Report

## 1. Verdict

**QA verdict: `NOT READY`.**

W2 local automation hardening is implemented and the sports UI dependency issue B60-P1-023 is closed. Real Test5 API/UI R2 remains externally blocked, and backend dependency audit found one unaccepted high vulnerability. The maximum target remains `LOCAL HARDENING COMPLETE / EXTERNAL BLOCKED`, but the repository cannot claim that target while B61-P1-001 is FAIL and other locally controlled Batch 61 MUST items remain NOT RUN.

No Test5 VPN switch, Test5 request, production request, production write, or Test5 write journey was performed.

## 2. Scope and baseline

| Field | Value |
| --- | --- |
| Date | `2026-08-01` |
| Executor/workflow | Codex / Agent Team |
| Branch | `feature/batch-61-sports-acceptance-and-supply-chain` |
| Base | `origin/main@174e002fbe53d75d49aaf09c269fac622a4c7c58` after W1 PR #89 |
| Worktree ports | frontend `5198`, backend `8028` |
| Scope | sports Playwright truthfulness, production smoke truth contract, Midscene supply chain, API/UI R2 cases/preflight/evidence |
| External scope | Test5 and production execution not authorized; write journeys separately blocked |

## 3. Implementation verification

| Area | Command/check | Result |
| --- | --- | --- |
| API preflight lint | `python -m ruff check tests/automation/api/batch61` | PASS |
| API preflight tests | `python -m pytest tests/automation/api/batch61/test_preflight.py -q` | PASS, `16/16` |
| Sports clean install | `npm ci` in `tests/automation/ui` | PASS, 284 packages |
| Sports production audit | `npm audit --omit=dev` | PASS, 0 vulnerabilities |
| Sports typecheck | `npm run typecheck` | PASS |
| Sports security | `npm run test:security` | PASS, `17/17` |
| Sports collection | explicit `test5` + `https://example.invalid` collection-only configuration, `npx playwright test --list` | PASS, `38 tests in 9 files`; no test requests |
| Missing-input behavior | unconfigured collection and missing test-data probe | PASS for fail-closed semantics: structured `B61-BLOCKED:<KEY>`, no browser/Test5 traffic |
| Production smoke contract | `npx playwright test specs/production-smoke-contract.spec.ts --project=chromium` | PASS, `6/6` |
| Backend Playwright collection | `npx playwright test --list` | PASS, `36 tests in 3 files`; production specs collected only |
| Backend F821 | `python -m ruff check app/ --select F821` | PASS |
| Backend full pytest | `python -m pytest -q` | final PASS, `976 passed, 3 skipped, 0 failed` |
| Frontend install/audit | `npm ci` | PASS, 560 packages audited, 0 vulnerabilities |
| Frontend typecheck/tests/build | `npm run typecheck`; `npm test`; `npm run build` | PASS, Vitest `291/291`, build PASS |

The first complete backend pytest attempt returned `973 passed, 3 skipped, 3 failed`. The complete failure set was:

- `test_backend_build_context_contains_runner_and_root_lanhu_submodule`
- `test_backend_declares_all_pinned_lanhu_runtime_dependencies`
- `test_pinned_runtime_without_optional_login_symbols_is_supported`

All three were caused by the required `lanhu-mcp` submodule not being initialized in the new worktree. After `git submodule update --init --recursive -- lanhu-mcp`, the three targeted tests passed and the full suite passed `976/3 skipped`. No source change was used to mask the environment failure.

## 4. Supply-chain result

| Finding | Result |
| --- | --- |
| Sports UI baseline | 7 high / 9 moderate / 4 low |
| Sports UI final | 0 vulnerabilities after `@midscene/web 1.10.8` and exact overrides for `js-yaml 4.3.0`, `sharp 0.35.0`, `uuid 11.1.1` |
| Backend observation | exact isolated `pip-audit 2.10.1`; 118 locked dependencies; exit 1; one vulnerability |
| Backend finding | `ecdsa 0.19.2`; `PYSEC-2026-1325`; `GHSA-wj6h-64fc-37mp`; `CVE-2024-23342`; GitHub severity high, CVSS 7.4; no patched version |
| Exploitability context | advisory affects ECDSA signing/key generation/ECDH; current application config is HS256; verification-only is not affected according to the advisory |
| QA disposition | B61-P1-001 `FAIL`; no named security owner, expiry, or approval exists; W2 scope excludes backend runtime/requirements replacement |

The raw pip-audit JSON was written only to a system temporary directory outside Git. The committed sanitized summary is `work-logs/evidence/batch-61-sports-platform-validation/supply-chain/README.md`.

## 5. R2 execution totals

| Matrix | PASS | FAIL | BLOCKED | NOT RUN | Total |
| --- | ---: | ---: | ---: | ---: | ---: |
| API P0 | 0 | 0 | 13 | 0 | 13 |
| API P1 | 0 | 0 | 3 | 0 | 3 |
| UI P0 | 0 | 0 | 20 | 0 | 20 |
| UI P1 | 0 | 0 | 3 | 0 | 3 |
| Combined | 0 | 0 | 39 | 0 | 39 |

All 39 cases are BLOCKED because the VPN window, six current contracts, least-privilege Secret reference, stable business keys, rate/retention/cleanup package and accountable owners are absent. Test5 request count is 0, browser count is 0, and Batch 61 sports success screenshot count is 0. Local unit/contract PASS is not included in the R2 totals.

## 6. Issue disposition

| Issue | W2 status | Evidence boundary |
| --- | --- | --- |
| B60-P0-001 | BLOCKED | deterministic login and no-AI credential contract pass locally; real R2 session/artifact scan absent |
| B60-P0-002 | BLOCKED | deep redaction/canary unit contract passes; real R2 trace/JSON/HTML/log absent |
| B60-P1-012 | BLOCKED | no silent skips, stable keys, API/business oracles and read-only admin specs implemented; real data execution absent |
| B60-P1-013 | BLOCKED | missing credential/API/business result smoke false-green regressions pass; real authorized target absent |
| B60-P1-023 | PASS | sports npm production audit 0 plus type/security/collection compatibility gates |
| B60-BLK-001 | BLOCKED | Test5 prerequisite package still unassigned |
| B61-P1-001 | FAIL | backend high vulnerability has no patch or approved risk acceptance |

## 7. Release gates

| Gate | Result | Reason |
| --- | --- | --- |
| A01/A02 baseline/isolation | PASS for W2 | worktree metadata, base SHA, branch, ports and scope verified |
| A03/A04 sports case/API assertions | BLOCKED | 16 API and 23 UI rows designed at 100% positive/negative feature coverage; no real R2 execution |
| A05/A06/A07/A08 | BLOCKED | roles, cross-user data, transaction/ledger, idempotency and pagination fixtures absent |
| A09 browser E2E | BLOCKED | no Test5 browser run or three-viewport success evidence |
| A11 automation/supply chain | FAIL | tests pass, but B61-P1-001 high remains unaccepted |
| A12 evidence consistency | PASS for W2 checkpoint | issue/matrix/results/readiness/PC totals reconciled; no fake evidence |
| A14 PC snapshots | BLOCKED | zero verified Test5 normal-success images |

## 8. Required next actions

1. Backend security owner must choose a replacement for the `python-jose`/`ecdsa` chain or provide a named, expiring, reviewable risk acceptance. This requires a separate backend-scoped change and full auth regression.
2. Product/environment owners must provide the Test5 prerequisite package using Secret references, not secret values in chat or Git.
3. After explicit VPN authorization, execute the 16 API and 23 UI R2 rows read-only first; write journeys remain separately authorized.
4. Leader verdict remains pending until Draft PR checks pass and the user reconfirms Codex as executor and authorizes final audit/merge.
