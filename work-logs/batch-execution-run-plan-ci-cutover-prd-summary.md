# Batch PRD — ExecutionRun Plan/CI cutover (PR-03)

## mode
full

## 目标
将 TestPlan execute-all 与 CI 触发路径迁移到 canonical Campaign → ExecutionRun，停止 canonical 路径的新 PlanExecutionJob 写入。

## 范围
- TestPlan 中已迁移的 API cases 物化为 CampaignItem，并调用 start_campaign。
- 保留 ensure_plan_execution_ready 的环境/base_url/token 预检。
- 增加生产环境 operation guard。
- execute-all 的 async_mode 不再创建 PlanExecutionJob。
- CI 不得直接启动旧 queue/worker/Playwright executor。

## 验收
1. execute-all 返回 campaign_id + run_ids。
2. PlanExecutionJob 新写入为 0。
3. 环境预检与生产 confirm guard 保留。
4. 未迁移用例继续 fail-closed。
5. 架构守卫扫描 execute-all 和 CI workflows。
