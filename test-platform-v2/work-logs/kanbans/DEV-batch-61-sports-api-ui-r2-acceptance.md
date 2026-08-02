# Dev Kanban - Batch 61 Sports API/UI R2 Acceptance

## Project information

| Field | Value |
| --- | --- |
| Project | Batch 61 sports API/UI R2 acceptance |
| Branch | `feature/batch-61-sports-acceptance-and-supply-chain` |
| Base | `origin/main@174e002fbe53d75d49aaf09c269fac622a4c7c58` |
| Worktree | `F:/CamelTv-worktrees/codex-batch-61-sports-acceptance-and-supply-chain` |
| Executor | Codex / Agent Team |
| Frontend/backend ports | `5198` / `8028` |
| PRD | `../batch-61-sports-api-ui-r2-acceptance-prd-summary.md` |
| PM plan | `../batch-61-sports-api-ui-r2-acceptance-pm-plan.md` |
| Created/updated | 2026-08-01 |

## Delivery slices

| # | Slice | Plan | Code | Self-test | Review | Merge | Notes |
| --- | --- | :---: | :---: | :---: | :---: | :---: | --- |
| 1 | Baseline and false-green contract | completed | completed | completed | pending | pending | Local truth contracts green |
| 2 | Midscene 1.x supply-chain closure | completed | completed | completed | pending | pending | UI runtime audit: 0 vulnerabilities |
| 3 | Sports journeys and read-only admin | completed | completed | completed | pending | pending | 38 tests collected; R2 externally blocked |
| 4 | API/UI case assets and preflight runner | completed | completed | completed | pending | pending | API 16 + UI 23 rows, no fake pass |
| 5 | Full regression and evidence reconciliation | completed | completed | completed | pending | pending | Local QA complete; external/ecdsa blockers preserved |

## Current position

```text
Batch 61 W2 - local implementation and QA complete
|- completed: W1 PR #89 merged; isolated W2 worktree verified
|- completed: explicit preconditions, stable test-data contract, deterministic business/API oracles
|- completed: Midscene 1.10.8; UI npm audit 0; security 17/17; sports collection 38/9
|- completed: production smoke truth contract 6/6; backend collection 36/3
|- completed: API preflight 16/16; API 16 and UI 23 R2 case/result/evidence assets
|- completed: backend 976/3 skip; frontend 291/291 + typecheck/build
|- blocked: Test5 package and write authorization absent; no external traffic executed
|- failed: backend ecdsa high has no fix/acceptance and is outside W2 runtime scope
|- next: internal review, user push authorization, Draft PR; no Leader verdict before final confirmation
```

## Blockers and risks

| Blocker | Severity | Owner | Unblock condition |
| --- | --- | --- | --- |
| Test5 VPN/window and six current contracts | P0 | `UNASSIGNED` | Written window plus versioned contract exports and gateway routes |
| Test5 least-privilege account and stable business keys | P0 | `UNASSIGNED` | Validity/scope/revocation plus named stable records |
| Sports write journeys | P0 | `UNASSIGNED` | Separate authorization, disposable identity, limit, idempotency, audit and cleanup owner |
| Operations read-only account/address | P1 | `UNASSIGNED` | Authorized endpoint and least-privilege credentials |
| Backend `ecdsa 0.19.2` high | P1 | `UNASSIGNED` | Replace/remove affected dependency or document named, expiring security acceptance; app currently uses HS256 but that is not acceptance |
| Backend dependency audit tool approval | P1 | `UNASSIGNED` | Check in an exact approved audit tool version; isolated 2.10.1 result remains observational evidence |

## Baseline evidence

| Check | Result |
| --- | --- |
| `npm ci` | exit 0; 284 packages installed from upgraded lock |
| `npm audit --omit=dev` | exit 0; 0 vulnerabilities |
| `npm run typecheck` | exit 0 |
| `npm run test:security` | exit 0; 17/17 passed |
| `npx playwright test --list` | exit 0; 38 tests in 9 files with explicit `.invalid` collection target |
| production smoke contract | exit 0; 6/6 passed; 36 tests in 3 files collected |
| backend full | F821 pass; 976 passed, 3 skipped, 0 failed |
| frontend full | 291/291, typecheck and build pass |
| backend pip audit observation | 118 dependencies; 1 high `PYSEC-2026-1325`; exit 1 |

## Batch record

### 2026-08-01 - W2 startup

- W1 PR #89 was merged to `main` before W2 creation.
- W2 was created from `origin/main@174e002` and Agent Team metadata passed verification.
- External Test5 and write operations remain blocked and were not attempted.
- Parallel subagents were unavailable due account quota; implementation continues in the confirmed Codex worktree without changing scope or evidence rules.

### 2026-08-01 - W2 local QA checkpoint

- No Test5 VPN switch, Test5 request, production request, or write journey was performed.
- Missing runtime/data inputs fail before browser setup using `B61-BLOCKED:<KEY>`.
- API R2 remains 16/16 BLOCKED; UI R2 remains 23/23 BLOCKED; PC success screenshots remain 0.
- The original sports UI supply-chain issue is closed locally; the newly observed backend ecdsa high is tracked separately as B61-P1-001 FAIL.
