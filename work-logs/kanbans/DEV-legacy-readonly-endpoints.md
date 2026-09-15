# Dev Kanban — Legacy readonly endpoints

> Batch: `legacy-readonly-endpoints` | Executor: Codex | Workflow: agent-team

## Progress

| Slice | Design | Code | Self-test | QA | Merge |
|---|---:|---:|---:|---:|---:|
| Legacy task mutation routes → 410, no writes | ✅ | ✅ | ✅ | ⏳ | ⏳ |
| Legacy runner mutation routes → 410, no writes | ✅ | ✅ | ✅ | ⏳ | ⏳ |
| Historical task UI read-only + execution-center link | ✅ | ✅ | ✅ | ⏳ | ⏳ |
| Architecture guard + focused regression | ✅ | ✅ | ✅ | ⏳ | ⏳ |
| Full backend/frontend regression and PR evidence | ✅ | ✅ | ✅ | ⏳ | ⏳ |

## Current position

`Batch legacy-readonly-endpoints — verification`

- Backend readonly route changes: complete.
- Frontend historical task view: complete.
- Focused backend tests: 48 passed.
- Architecture guard: 10 passed.
- Frontend typecheck/lint/targeted Vitest: passed.
- Full regression/build/QA complete; next: commit/push, required checks, Leader verdict, merge.

## Evidence so far

- `backend/tests/test_api_task_worker.py`
- `backend/tests/test_batch206_runner.py`
- `test-platform-v2/tests/test_execution_architecture_guard.py`
- `frontend/src/pages/apitest/components/TaskTab.test.tsx`

## Notes

- No schema change.
- No legacy table/model/worker deletion.
- Canonical `ExecutionRun` remains the only write path for new execution.

