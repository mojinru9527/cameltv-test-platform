# Batch PRD — ExecutionRun API cutover (PR-02)

## mode
full

## 背景
PR-01 已合入 canonical Campaign → ExecutionRun 入口。PR-02 需要停止 API 批量执行的新 legacy 写入，将 `/api/v1/apitest/tasks` 改为 Campaign 适配器。

## 目标
- POST `/apitest/tasks` 不再创建 ApiExecutionTask / Item，也不启动 api_task_worker。
- 对已迁移为 canonical Scenario 的 API 用例，创建 TestCampaign + CampaignItem，并通过 start_campaign 生成 ExecutionRun。
- 保留 legacy task 查询/取消/重跑接口用于历史数据。
- 未迁移用例明确返回 409，不静默双写或伪造 Run。

## 非目标
- 不删除 ApiExecutionTask 表或历史 worker。
- 不实现 TestPlan/CI cutover（PR-03）。
- 不新增第二套执行状态机。

## 验收
1. 新 `/tasks` 请求产生 Campaign + Run，ApiExecutionTask 新写入为 0。
2. 新请求不会调用 api_task_worker。
3. 缺失 canonical 映射时，请求 fail-fast 且不留下 Campaign/Run/legacy rows。
4. 环境项目隔离与生产 confirm guard 保持。
5. 历史 task 查询仍可用。
