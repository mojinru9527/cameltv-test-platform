# PM Plan — ExecutionRun canonical migration

## 目标
按实施包顺序完成 PR-01 → PR-09，任何阶段不得并行删除或重新设计执行模型。

## 切片
| Slice | 交付 | 前置 | 当前 |
|---|---|---|---|
| PR-01 | Campaign 编排 + canonical Run API + migration/tests | 无 | 进行中 |
| PR-02 | API batch 入口切 Campaign，ApiExecutionTask 停止新写 | PR-01 合入 | 待开始 |
| PR-03 | TestPlan/CI 切 Campaign，PlanExecutionJob 停止新写 | PR-02 合入 | 待开始 |
| PR-04 | API/UI/External Runner 统一 claim/heartbeat/report/cancel | PR-03 合入 | 待开始 |
| PR-05 | EvidenceArtifact / object storage 统一 | PR-04 合入 | 待开始 |
| PR-06 | AiTask 外置为 AiJob + Local Agent claim/report | PR-05 合入 | 待开始 |
| PR-07 | AI provider/shadow/gateway 冻结为运维/评估用途 | PR-06 合入 | 待开始 |
| PR-08 | Legacy readonly，自动 bridge 仅迁移命令可调用 | PR-07 合入 | 待开始 |
| PR-09 | 满足删除条件后移除旧 executor/queue | PR-08 + 一个版本周期 | 待开始 |

## PR-01 工程任务
1. 新增 campaign models/contracts/service/router。
2. 注册模型与 v1 router。
3. 新增 Alembic migration，SQLite/PostgreSQL 兼容。
4. 增加架构守卫、service test、API smoke。
5. 运行后端 F821、相关 pytest、架构守卫、Alembic 单头。

## 风险与控制
- 风险：新 Campaign 再次复制 Run 状态机。控制：service 仅调用现有 `ExecutionService.create_run`。
- 风险：旧库安装时缺表。控制：迁移使用 inspector 幂等建表，并确保模型进入 Base.metadata。
- 风险：跨项目泄露。控制：Campaign 查询强制 project_id。
