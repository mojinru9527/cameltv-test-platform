# Batch 61 Sports API/UI R2 Acceptance - Design Spec

> **Design** | Date: 2026-08-01 | Status: Ready

## 1. Scope and interaction model

This work changes automation and acceptance semantics, not the testing-platform visual UI. The primary designed surface is the machine-readable result contract used by Playwright, API preflight, QA reports, and release evidence.

```text
environment + authorization + contract/data manifest
  -> preflight
     -> READY: browser/network execution may start
     -> BLOCKED: stop before side effects and name missing key/owner
  -> assertion layers
     -> DOM/business result
     -> API response/traffic policy
     -> data/admin/audit reconciliation when applicable
  -> redacted evidence and result row
```

## 2. Status contract

| Status | Meaning | Required fields | Forbidden behavior |
| --- | --- | --- | --- |
| `PASS` | Every required assertion was executed and satisfied | case ID, environment, SHA, assertion summary, evidence reference | Using page load, script completion, Mock data, or historical evidence as a substitute |
| `FAIL` | Execution occurred and a required assertion failed | expected, actual, defect ID/evidence | Downgrading to skip or hiding the failed assertion |
| `BLOCKED` | Execution could not start or complete because an external prerequisite is absent | stable code, missing key, accountable owner or `UNASSIGNED`, unblock condition | Opening a browser/sending network traffic when preflight is incomplete |
| `NOT RUN` | Locally executable work has not run | reason and next action | Treating it as pass |

The structured blocked code format is `B61-BLOCKED:<KEY>`. Human-readable messages may be localized, but the code and owner fields remain stable for automation.

## 3. Environment and authorization contract

| Field | Rule |
| --- | --- |
| Target environment | Explicit `test5` or `production`; no default URL or environment |
| Base URL | Explicit HTTPS URL and allowlisted host |
| Run level | Explicit `readonly` or `write-authorized` |
| Production methods | GET/HEAD only |
| Test5 write | Separate written authorization, disposable identity, limit, idempotency key, cleanup API/owner |
| Credentials | Process secret only; never AI prompt, command output, screenshot, trace, JSON/HTML report, or Git |

## 4. Stable test-data contract

Data selection must use named business keys from a manifest. Selectors such as first row, random article, or first available package are invalid acceptance inputs.

| Key family | Required examples |
| --- | --- |
| Identity | anonymous, normal, low-balance, first-purchase, used-eligibility, operations-readonly |
| Content | recommended author/Yield order, category, pinned/free/paid article, locked/unlocked prediction |
| Settlement | settled Win and Loss prediction |
| Commerce | Bonus and non-Bonus packages, bounded disposable order only when authorized |

## 5. Assertion design

Every selected API case includes parameter, business, and response assertions. Every P0 UI journey includes a visible business result and the corresponding API assertion; data/admin/audit reconciliation is required for writes and for read-only order/content verification where the endpoint exists.

AI vision may assist element location only. It cannot receive credentials, tokens, PII, raw responses, or decide payment/refund/entitlement/balance correctness.

## 6. Evidence design

- Evidence filename begins with the case ID.
- Evidence records full code SHA, date, target environment, and sanitized correlation ID.
- URL, query, headers, request body, response headers/body, traces, HTML, JSON, logs, and screenshots are scanned for injected canaries.
- Unknown binary or unparsable sensitive bodies fail closed rather than being persisted raw.
- A `1440x900` screenshot is required for each verified normal PC function; screenshots do not replace assertion results.

## 7. Error and empty states

| Condition | Designed result |
| --- | --- |
| Missing target URL/environment/run level/allowlist | `BLOCKED` before browser launch |
| Missing credentials or rejected login | `BLOCKED` for absent authorization; `FAIL` for supplied but rejected credentials |
| Zero API assets or missing business fixture | `BLOCKED`/`FAIL` according to ownership, never `PASS` |
| Unsupported browser capability | Playwright skip only with a fixed issue ID |
| Network/API failure after valid preflight | `FAIL` with redacted request/response evidence |
| Unauthorized write journey | `BLOCKED` before request construction |

## 8. Design review

The design is approved for implementation because it preserves the Batch 61 fail-closed rules and does not introduce a new product UI. External R2 success-state screenshots and final visual review remain blocked on the Test5 prerequisite package.
