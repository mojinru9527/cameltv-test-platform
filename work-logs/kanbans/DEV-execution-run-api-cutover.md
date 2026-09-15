# Dev Kanban — ExecutionRun API cutover

| Field | Value |
|---|---|
| Project | CamelTv test-platform-v2 |
| Branch | feature/execution-run-api-cutover |
| Base | main @ PR-440 merge |
| Current | PR-02 code |

## Slices
| # | Slice | Spec | Code | Test | QA | Merge |
|---|---|---|---|---|:---:|:---:|
| 1 | Run ↔ Campaign link | ✅ | ✅ | ✅ | ✅ | ⏳ |
| 2 | API case adapter | ✅ | ✅ | ✅ | ✅ | ⏳ |
| 3 | `/apitest/tasks` cutover | ✅ | ✅ | ✅ | ✅ | ⏳ |
| 4 | Legacy read compatibility | ✅ | ✅ | ✅ | ✅ | ⏳ |

## Rule
No new execution model. New API task writes go only to Campaign/Run; ApiExecutionTask is historical compatibility.
