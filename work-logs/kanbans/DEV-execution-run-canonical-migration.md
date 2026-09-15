# Dev Kanban — ExecutionRun canonical migration

| Field | Value |
|---|---|
| Project | CamelTv test-platform-v2 |
| Branch | feature/execution-run-canonical-migration |
| Workflow | Agent Team / Codex |
| Current | PR-01 |
| Created | 2026-09-15 |

## Slice progress

| # | Slice | Spec | Code | Self-test | QA | Merge |
|---|---|---|---|---|:---:|:---:|
| 1 | PR-01 Campaign canonical | ✅ | ✅ | ✅ | ✅ | ⏳ |
| 2 | PR-02 API cutover | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ |
| 3 | PR-03 Plan + CI cutover | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ |
| 4 | PR-04 Runner protocol | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ |
| 5 | PR-05 Artifact cutover | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ |
| 6 | PR-06 AI external-only | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ |
| 7 | PR-07 AI freeze | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ |
| 8 | PR-08 Legacy readonly | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ |
| 9 | PR-09 Legacy delete | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ |

## Current position

```
PR-01
├── completed: Product/PM/Design facts + package baseline confirmation
├── completed: campaign module + migration + tests
├── in progress: commit / push / PR / required checks
└── next after merge: PR-02 API cutover
```

## Rules
- 每个切片完成即 commit；不在 control worktree 开发。
- PR-02..09 必须基于已合入最新 main 的下一批次执行。
- 不新增 Run/Queue 事实模型。
