# Dev Kanban — Legacy delete final

## Project

| Field | Value |
|---|---|
| Batch | legacy-delete-final (PR-09) |
| Executor | codex |
| PRD | [batch-legacy-delete-final-prd-summary.md](../batch-legacy-delete-final-prd-summary.md) |
| PM plan | [batch-legacy-delete-final-pm-plan.md](../batch-legacy-delete-final-pm-plan.md) |
| QA report | [batch-legacy-delete-final-qa-report.md](../batch-legacy-delete-final-qa-report.md) |

## Slices

| # | Slice | Design | Code | Self-test | Review | Merge |
|---|-------|:------:|:----:|:---------:|:------:|:-----:|
| 1 | Delete Legacy executors | ✅ | ✅ | ✅ | 🔄 | ⏳ |
| 2 | Explicit bridge migration | ✅ | ✅ | ✅ | 🔄 | ⏳ |
| 3 | Read-only history guards | ✅ | ✅ | ✅ | 🔄 | ⏳ |

## Current Position

Local implementation and regression evidence are complete. Waiting for Draft
PR checks, final audit, merge and production deployment.

## Risks

- Historical tables remain intentionally in place; physical retention is a
  separate archival decision.
