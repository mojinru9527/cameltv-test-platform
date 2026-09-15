# Batch PM Plan — Legacy execution readonly endpoints

## Tasks

| ID | Task | Owner | Output |
|---|---|---|---|
| T1 | Make legacy task mutation routes return `410` before any write | Dev | `backend/app/api/v1/apitest_tasks.py` |
| T2 | Make legacy runner mutation routes return `410` | Dev | `backend/app/api/v1/api_runner.py` |
| T3 | Remove legacy mutation actions from historical task UI and link to canonical execution center | Dev | `frontend/src/pages/apitest/components/TaskTab.tsx`, API client |
| T4 | Add regression tests for HTTP semantics and zero row mutation | QA/Dev | backend + frontend tests |
| T5 | Record QA evidence and Leader verdict | QA/Leader | work-logs artifacts |

## Order and dependencies

`T1/T2 → T3 → T4 → T5`

## Out of scope

- Deleting Legacy tables/models/workers
- Mapping historical rows to canonical runs
- Changing canonical ExecutionRun APIs
- Changing UI paths other than the historical API task view

## Risks

| Risk | Mitigation |
|---|---|
| Hidden frontend caller still invokes legacy mutation | Remove API client exports/usages and run Vitest/typecheck |
| Read-only route breaks project isolation semantics | Keep project ownership lookup and return `404` for foreign rows before `410` |
| Test suite encodes old behavior | Rewrite legacy mutation tests to assert `410` and no state change |
