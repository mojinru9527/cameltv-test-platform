# QA Report — Legacy readonly production evidence

> Batch: `legacy-readonly-evidence` | Date: 2026-09-16 | Result: **PASS**

## Checks

| Check | Result |
|---|---|
| `python -m pytest tests/test_legacy_delete_gate.py -q` | ✅ passed |
| Production mutation probes | ✅ task cancel/retry/delete and runner claim all 410 |
| Health / login | ✅ health 200, login user_id=4 |
| Container state | ✅ backend/frontend/runner/aitde-worker/ai-gateway/postgres healthy |
| Legacy fingerprint check | ✅ no new/updated rows, fingerprints unchanged |
| Historical mapping | ✅ API 1999/1999, UI 203/203 |
| Restore drill | ✅ isolated PostgreSQL restore passed |

## Gate state

- `legacy_urls_readonly_or_redirect`: true
- `historical_mapping_complete`: true
- `rollback_restore_drill_success`: true
- `legacy_new_writes_zero_full_cycle`: false until observation end
- `product_qa_architecture_signoff`: false

No runtime code or Legacy table was changed by this evidence batch.
