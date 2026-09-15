# Design Spec — Campaign → canonical ExecutionRun

## Canonical chain
`CampaignItem(asset/config) -> aitde.execution.service.create_run() -> ExecutionRun`

Campaign 不执行请求，不保存 runtime_status，不复制 Outcome。

## Data model
### test_campaign
project_id、name、type、requirement_version、environment_id、dataset_id、runner_selector_json、strategy_json、status、version、created_by、started_at、finished_at。

### test_campaign_item
campaign_id、asset_type、asset_id、sequence、depends_on_json、enabled、config_json。config 必须至少携带 `scenario_id`、`scenario_version_id`、`contract_version_id`、`environment_snapshot_id`，可选 `adapter_id`。

## API
`POST /api/v1/execution/campaigns/{campaign_id}/runs`
- 权限：`apitest:execute`
- project 必须来自当前 token context。
- 返回：`{campaign_id, run_ids}`。
- 错误：Campaign 不存在/跨项目 404；无 enabled item 400；Run 绑定错误沿用 AITDE APIException。

## Compatibility
PR-01 只新增 canonical 入口，不切换旧入口。PR-02+ 的兼容 endpoint 必须适配到本 Service，不能维护自己的状态机。

## Testing
- 单元：顺序物化、空 Campaign、跨项目。
- API：权限与响应 shape。
- 架构：禁止 `backend/app/modules/execution/models.py` 与新增 `*_execution_queue.py`。
- Migration：SQLite upgrade/downgrade smoke；Alembic 单 head。
