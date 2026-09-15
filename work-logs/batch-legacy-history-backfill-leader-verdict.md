# Leader Verdict — Legacy history backfill

> Batch: `legacy-history-backfill` | Mode: light | Date: 2026-09-16 | Executor: Codex | Decision: **APPROVED**

## Review

| Area | Verdict | Evidence |
|---|---|---|
| Scope | ✅ | Internal migration tool only; no new execution system or schema |
| Implementation | ✅ | Reuses `legacy_bridge.bridge_api_item` / `bridge_ui_run`; default dry-run; explicit `--apply` |
| API mapping | ✅ | Production API links 1999/1999; 1942 created with 0 failures |
| UI mapping | ✅ | Production UI links 203/203; 130 created with 0 failures |
| Idempotency | ✅ | Post-apply dry-run selected_items=0 and ui_selected_runs=0 |
| Legacy safety | ✅ | Three Legacy table fingerprints unchanged before/after migration |
| Restore drill | ✅ | Latest production dump restored into isolated PostgreSQL; key counts verified; temporary instance removed |
| Focused QA | ✅ | 5 passed; Ruff F821 passed |
| Full backend regression | ✅ | 2691 passed; only 3 pre-existing `test_session_credentials.py` failures |
| Dev gate | ✅ | `PASS_WITH_WARN`, HARD=0, route guards passed |

## Gate changes

- `historical_mapping_complete`: `true`
- `rollback_restore_drill_success`: `true`
- `legacy_new_writes_zero_full_cycle`: remains false for the active observation cycle
- `legacy_urls_readonly_or_redirect`: remains false until the release containing PR #451 reaches production
- `product_qa_architecture_signoff`: remains false

## Conditions

No new C condition. The remaining PR-09 work is already covered by the observation window and release deployment gate.

## 流程回写

| 发现 | 处理 | 落点 |
|---|---|---|
| Historical UI runs were not covered by the first API-only audit | Extended backfill to `UI_RUN` using the existing `bridge_ui_run` | `scripts/backfill_legacy_execution_links.py` |
| Malformed Legacy JSON would be rejected by evidence sanitizer | Convert non-structured request/response snapshots to a safe placeholder | `_safe_evidence` |
| Restore and mapping evidence needed to update the machine gate | Recorded production evidence and flipped the two satisfied flags | `work-logs/legacy-history-backfill-production-20260916.md`, `legacy_delete_gate.json` |
