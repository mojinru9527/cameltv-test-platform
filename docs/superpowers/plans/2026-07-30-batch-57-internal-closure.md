# Batch 57 Internal Closure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close every Batch 56/57 acceptance gap that can be completed locally without VPN, production infrastructure, SMTP, ELK credentials, physical devices, or an external AI credential.

**Architecture:** Keep deterministic extraction as the fallback, add one reusable DeepSeek-compatible JSON client for semantic analysis, and make every degraded result explicit instead of presenting a stub as success. Produce Linux-native dependency evidence and a J01–J22 evidence matrix only from commands that actually ran. Preserve the two-environment model: local development now, unprovisioned production later.

**Tech Stack:** FastAPI, SQLAlchemy, httpx, BeautifulSoup, pytest, React/Vitest, Docker/Linux, pip-licenses, npm audit.

---

## Task 1: Replace the knowledge-center placeholder behavior

**Files:**
- Create: `test-platform-v2/backend/app/services/knowledge/llm_json_client.py`
- Modify: `test-platform-v2/backend/app/services/knowledge/version_differ.py`
- Modify: `test-platform-v2/backend/app/services/knowledge/attachment_extractor.py`
- Modify: `test-platform-v2/backend/app/services/knowledge/navigates_to_extractor.py`
- Test: `test-platform-v2/backend/tests/test_knowledge_ai_closure.py`

- [ ] Write failing tests for missing credentials, valid structured responses, malformed responses, attachment failure visibility, semantic version-diff changes, DOM targets, and OCR-text-assisted navigation.
- [ ] Run `pytest tests/test_knowledge_ai_closure.py -q` from `test-platform-v2/backend` and confirm the new tests fail for the intended placeholder behavior.
- [ ] Implement an asynchronous JSON-only client using `settings.ai_api_base_url`, `settings.ai_model`, `settings.ai_api_key`, and `settings.ai_timeout_seconds`.
- [ ] Reject missing keys and malformed/non-object model responses with a typed availability error; never return fabricated content.
- [ ] In `version_differ.py`, send only sanitized module/page/OCR text, merge validated AI classifications into the rule result, and append an explicit warning when the AI path is unavailable.
- [ ] In `attachment_extractor.py`, validate the model schema and treat unavailable/invalid AI analysis as a failed attachment rather than incrementing `processed`.
- [ ] In `navigates_to_extractor.py`, parse real DOM link attributes with BeautifulSoup and use sanitized OCR/DOM text for DeepSeek semantic inference. Do not claim DeepSeek performs OCR or upload a screenshot.
- [ ] Re-run `pytest tests/test_knowledge_ai_closure.py tests/test_batch48_lanhu_attachment_contract.py -q`.

Expected behavior example:

```python
try:
    payload = await call_json_model(system_prompt=..., user_payload=...)
except LLMUnavailableError as exc:
    result.warnings.append(f"AI semantic analysis unavailable: {exc}")
    return result
```

## Task 2: Complete the Linux backend license evidence

**Files:**
- Create: `test-platform-v2/work-logs/evidence/batch-57/backend-linux-licenses.json`
- Create: `test-platform-v2/work-logs/evidence/batch-57/backend-linux-license-command.txt`
- Modify: `test-platform-v2/work-logs/batch-57-license-audit.md`
- Modify or create if distribution requires it: `THIRD_PARTY_NOTICES.md`

- [ ] Build a Python 3.12 Linux container from the exact `requirements.lock` with hash verification.
- [ ] Install the audit utility outside the application lock, export all installed distribution names, versions, licenses, URLs, and license text locations as JSON.
- [ ] Verify the 111 locked packages are present at exact versions; record lock SHA-256, container image digest, command, UTC timestamp, and exit code.
- [ ] Fail the audit if any third-party dependency is GPL/AGPL, unknown, unlicensed, or absent from the reviewed set.
- [ ] Record `psycopg2-binary` as LGPL with PostgreSQL linking exceptions and state the repository’s binary-distribution/NOTICE treatment without claiming legal advice.
- [ ] Update the report from `PARTIAL` to the status supported by the Linux evidence.

## Task 3: Reconcile J01–J22 with executable evidence

**Files:**
- Modify: `docs/work-logs/batch-56-production-acceptance-execution-matrix.md`
- Create: `test-platform-v2/work-logs/batch-57-j01-j22-atomic-evidence.md`
- Modify: `tests/requirements/traceability-matrix/matrix-v14.csv` only if a real uncovered requirement is found

- [ ] Inventory existing tests for every J item and map exact test node IDs.
- [ ] For each locally executable J item, run at least one positive and one negative path.
- [ ] For API items, record all three validations: HTTP status, response schema/shape, and business semantics/side effect.
- [ ] Mark external-only cases as `SKIPPED/DEFERRED` with their exact prerequisite; do not convert missing VPN, SMTP, ELK, device, production-server, or DeepSeek credentials into a pass.
- [ ] Verify the 108 non-comment requirements in `matrix-v14.csv` remain covered and distinguish the 25 separator/comment rows from requirements.
- [ ] Update J01–J22 statuses only when the cited evidence supports the change.

Evidence row format:

```text
J05 | positive test node | negative test node | status assertion |
schema assertion | business-state assertion | command exit code | disposition
```

## Task 4: Re-check lifecycle integrity defects

**Files:**
- Modify only the backend/frontend lifecycle files confirmed by the read-only audit
- Add focused tests beside the affected API/service/frontend suites

- [ ] Confirm audit events are committed in the same durable transaction as plan, execution, report, schedule, and defect actions.
- [ ] Make failure-to-defect triage reachable through a real backend route and a mounted frontend entry point.
- [ ] Enforce project ownership on defect update paths as well as create paths.
- [ ] Add idempotency/concurrency protection for scheduled and manual execution and ensure a schedule cannot be marked complete while its execution remains pending.
- [ ] Emit plan-complete notifications only after the plan reaches its actual completion condition, covering manual, batch, API, and schedule paths.
- [ ] Add focused regression tests for every repaired invariant.

## Task 5: Execute production-grade local regression

**Files:**
- Modify: `test-platform-v2/work-logs/batch-57-production-acceptance-report.md` or the current canonical Batch 57 report

- [ ] Backend hard gate: `ruff check app/ --select F821`.
- [ ] Backend focused tests for Tasks 1, 3, and 4.
- [ ] Backend full regression: `pytest`.
- [ ] Frontend hard gates: `npm run typecheck` and `npm run build`.
- [ ] Frontend full regression: `npm test`.
- [ ] Dependency checks: Linux backend evidence, `npm audit --omit=dev`, and repository secret/debug-artifact scan.
- [ ] Verify `http://localhost:5173/` and `http://127.0.0.1:8000/health`.
- [ ] Record exact commands, exit codes, pass/fail totals, and known baseline failures in the canonical report.
- [ ] Review `git diff --check`, changed-file scope, and worktree metadata.
- [ ] Create local commits only. Before any push, present the mandatory change summary and request a fresh one-time push authorization using the repository wording.

## Plan self-review

- [x] The plan does not require any VPN state change or production write.
- [x] External prerequisites remain explicit and cannot be silently marked passed.
- [x] Tests precede code changes for the three known knowledge-center stubs.
- [x] AI and OCR responsibilities are separated: local OCR extracts text; DeepSeek performs permitted semantic analysis.
- [x] Evidence is generated from real executions and includes command identity and exit status.
- [x] No push, PR, or main-branch mutation is authorized by this plan.
