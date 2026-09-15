# Batch PRD — ExecutionRun canonical migration (PR-01)

## mode
full

## 背景
当前平台存在 API Task、Plan Job、Runner Task、UI Job 与 AITDE ExecutionRun 并行执行事实。优化文档要求不再新增执行体系，只把现有链路逐步迁移到仓库已有的 canonical `ExecutionRun`。

## 用户价值
- 测试工程师只面对一套 Campaign → Run 结果模型。
- Runner 只使用 claim / heartbeat / report / cancel 协议。
- 后续 API、Plan、CI、UI、AI 迁移不会继续制造第二套状态机。

## 本切片范围（PR-01）
- 新增 `campaign_execution` 编排模块：Campaign 与 CampaignItem。
- Campaign 执行只调用现有 `app.modules.aitde.execution.service.create_run()`。
- 暴露 `POST /api/v1/execution/campaigns/{campaign_id}/runs` canonical 入口。
- 增加数据库迁移、模型注册、架构守卫和最小服务/API 测试。
- 不修改旧 API/Plan worker 的执行行为；旧链路迁移从 PR-02 开始。

## 非目标
- 不创建第二套 Run、TaskRun、ExecutionQueue 或状态机。
- 不删除旧表，不在 PR-01 切换旧入口。
- 不重写 AITDE 绑定校验、Evidence、Outcome 逻辑。

## 验收标准
1. `test_campaign`、`test_campaign_item` 可通过迁移与 `Base.metadata.create_all` 创建。
2. Campaign 的 enabled items 按 sequence 逐个生成 canonical ExecutionRun。
3. 空 Campaign 或跨项目 Campaign 返回明确业务错误。
4. canonical API 文件和 service 不拥有 Run 状态机。
5. 架构测试阻止新增第二套 execution model/queue。
