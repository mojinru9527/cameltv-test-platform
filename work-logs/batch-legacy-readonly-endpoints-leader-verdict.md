# Leader Verdict — Legacy readonly endpoints

> Batch: `legacy-readonly-endpoints` | Date: 2026-09-15 | Executor: Codex | Decision: **APPROVED**

## Review

| Area | Verdict | Evidence |
|---|---|---|
| Product scope | ✅ | Legacy mutation URLs are read-only; history remains readable; no new execution system |
| PM sequencing | ✅ | Backend fail-closed first, then frontend historical view, then regression/evidence |
| Design | ✅ | 410 semantics, project isolation, read-only copy and `/executions` route are implemented |
| Dev implementation | ✅ | 13 files changed; no Legacy table/model/worker deletion; architecture guard added |
| QA | ✅ | Focused 48 passed; architecture guard 10 passed; frontend 710 passed; build/lint/typecheck passed |
| Full regression | ✅ | Backend 2687 passed; only 3 pre-existing `test_session_credentials.py` failures reproduce on clean main |
| CI | ✅ | PR #451 required checks all successful: 9 successful, 0 failing |

## Gate impact

This batch closes the implementation half of `legacy_urls_readonly_or_redirect` for the known writable Legacy execution routes. The production zero-write observation continues independently. It does **not** delete Legacy code or data.

Remaining PR-09 gate work stays visible: historical mapping completion, rollback/restore drill, and Product/QA/Architecture sign-off.

## Conditions

No new C condition is required for this batch. Existing PR-09 gate remains the source of truth.

## 流程回写

| 发现 | 处理 | 落点 |
|---|---|---|
| Legacy mutation routes remained callable after canonical cutover | Fail closed before DB writes and remove frontend mutation controls | `backend/app/api/v1/apitest_tasks.py`, `backend/app/api/v1/api_runner.py`, `frontend/.../TaskTab.tsx` |
| Architecture guard did not prevent legacy write-path reintroduction | Add source-level readonly guards | `test-platform-v2/tests/test_execution_architecture_guard.py` |
| Frontend multi-domain scope must be declared in worktree metadata | Record both backend/frontend scopes before audit | `.ai-worktree.json` (local metadata, not committed) |
