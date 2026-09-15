# PM Plan — ExecutionRun API cutover (PR-02)

## Slice scope
1. 扩展 canonical Run，记录 campaign_id / campaign_item_id。
2. 新增 API-case → Campaign adapter：解析 ScenarioAdapter 或 LegacyObjectMapping、环境快照、CampaignItem。
3. 替换 POST `/apitest/tasks` 为 canonical path。
4. 将 legacy worker import/call 移出 canonical endpoint。
5. 更新 route inventory、单测、隔离/生产 guard 测试和 QA 证据。

## Sequence
- schema/model
- adapter service + unit tests
- endpoint cutover + API tests
- regression
- PR / required checks / merge

## Risks
- 未迁移用例会返回 409：这是迁移门禁，不是业务执行失败。
- 历史 GET/cancel/retry 仍走 legacy tables：仅兼容历史数据。
- 环境快照必须 project-scoped，不能跨项目复用。
