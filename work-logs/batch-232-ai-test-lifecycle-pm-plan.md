# Batch 232 - AI Test Lifecycle PM Plan
> **PM** | Date: 2026-09-07

## 规格摘要

**原始需求**：需求输入后完成分析、拆解、三类用例生成、逐条执行录制、缺陷标记与复验，并区分需求测试、版本回归、生产回归。  
**目标时间**：本批完成可部署的首个闭环版本；生产真实 16.0.0 任务在发布后执行。

## 开发任务

### [ ] Task 1: 建立 VersionTask 与阶段 Mission 正式关系

**描述**：Mission 新增 `version_task_id`，创建/更新时校验同项目 VersionTask；API 输出关联字段。  
**验收标准**：跨项目关联被拒绝；一个 VersionTask 可关联多个不同类型 Mission；旧 Mission 保持可读。  
**涉及文件**：Mission model/schema/service/mapper、Alembic migration、Mission API 测试。  
**参考**：PRD US1。

### [ ] Task 2: 场景增加用例分类和需求角色

**描述**：ScenarioCandidate 与 TestScenarioVersion 增加 `case_type`、`requirement_role`、`module_key`；AI prompt 强制返回，列表和详情 API 输出。  
**验收标准**：仅接受 FUNCTIONAL/API/UI 与 NEW/CHANGED/IMPACTED_BASELINE；AI 缺字段时校验失败；确定性生成器也产生合法元数据。  
**涉及文件**：scenario schema/model/repository/service、intelligence provider/prompt、迁移与测试。  
**参考**：PRD US2。

### [ ] Task 3: 失败运行关联缺陷

**描述**：Defect 新增 `aitde_run_id`，提供从 AITDE run 创建缺陷的端点，并验证运行结果和租户边界。  
**验收标准**：仅失败/不确定结果可创建；缺陷回指原 run；跨项目不可访问；同一 run 重复创建时复用已有开放缺陷。  
**涉及文件**：defect model/schema/service、execution API、迁移与后端测试。  
**参考**：PRD US4。

### [ ] Task 4: Mission 生命周期聚合 API

**描述**：一次查询汇总六阶段数量、三类用例、需求角色、逐场景执行/证据/缺陷/复验，并返回同 VersionTask 的阶段 Mission。  
**验收标准**：返回值来自持久化事实；每条用例可追溯；旧数据明确 UNCLASSIFIED；无 N+1。  
**涉及文件**：新 lifecycle service/schema、missions router、后端聚合测试。  
**参考**：PRD US1/US3/US5。

### [ ] Task 5: Mission 概览改为真实工作台

**描述**：替换静态六卡，显示阶段导航、三类用例统计、需求角色统计、逐用例执行表和明确缺口。  
**验收标准**：Loading/Empty/Error/Data 四态；桌面/平板/移动无重叠；中文状态；单次 lifecycle 请求。  
**涉及文件**：missions API client、overview page、Vitest。  
**参考**：Design Spec。

### [ ] Task 6: 质量门禁与交付工件

**描述**：运行相关与全量门禁，完成 QA 报告、Leader Verdict、证据索引、看板，并按一次总确认进入 Draft PR。  
**验收标准**：命令、退出码、失败集合可追溯；C227-1 满足；required checks 全绿后才能 Leader APPROVED。  
**涉及文件**：work-logs 与 evidence。

### [x] Task 7: AI 缓存复用与成本遥测

**描述**：保留稳定公共提示前缀、同操作精确请求去重、OpenAI 官方缓存路由键，并把 OpenAI/DeepSeek usage 归一化写入 AI 操作记录。
**验收标准**：OpenAI/DeepSeek 两种命中字段可识别；非 OpenAI 端点无专用字段；歧义/意图相同请求从两次降为一次；调试抽屉区分 0% 与未提供。
**涉及文件**：共享 AI client、AITDE prompt/provider/runner、ai_ops service、AI Debug Drawer 与测试。
**参考**：PRD US6。

## 质量要求

- [ ] 后端 F821、相关 Pytest、全量 Pytest、Alembic 单头通过
- [ ] 前端 typecheck、build、相关 Vitest、全量 Vitest通过
- [ ] 概览无 N+1 请求，异步副作用可取消
- [ ] 所有新端点有权限和项目隔离测试
- [ ] UI 桌面 1440x900、平板 768x1024、移动 390x844 走查
- [ ] 无调试输出、凭据和生产秘密进入提交
- [x] 缓存指标只来自供应商 usage，不显示 Prompt 原文、缓存键或价格推算
