# Design Spec — API batch canonical adapter

## Canonical write path
`POST /api/v1/apitest/tasks`
→ validate API cases + production guard
→ resolve canonical binding for each case
→ TestCampaign + CampaignItem
→ `start_campaign()`
→ existing `ExecutionRun`

## Binding resolution
1. Prefer active `ScenarioAdapter` whose `source_asset_id` is the TestCase id.
2. Else use verified `LegacyObjectMapping(TEST_CASE → TEST_SCENARIO)` and the latest scenario version.
3. Else fail 409 with the unmapped case id.
4. Require `environment_id`; create/reuse an ad-hoc `EnvironmentSnapshot` for that environment.
5. Persist `campaign_id` and `campaign_item_id` on ExecutionRun for traceability.

## Compatibility
- Legacy `ApiExecutionTask` tables stay readable for historical rows.
- Cancel / retry / detail / curl / analysis endpoints remain legacy-compatible in PR-02.
- New POST response exposes `campaign_id`, `run_ids`, `status`, `total`.

## Tests
- adapter materialization and missing-binding fail-fast
- endpoint creates zero legacy task rows
- project isolation and production confirmation still block before writes
- clean app import, architecture guard, Alembic upgrade/downgrade
