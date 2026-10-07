"""执行运行时独立模块（平台简化批次）。

从 AITDE 抽离的**最小执行运行时**，服务于保留的计划/接口统一执行链路
（``app.modules.campaign_execution``）与证据包/执行节点协议：

- ``models`` / ``scenario_models`` / ``legacy_models``：统一执行事实表
  （ExecutionRun/EnvironmentSnapshot/ScenarioAdapter/TestScenario/LegacyObjectMapping 等），
  表名与迁移历史保持一致，删除 AITDE 后数据不迁移；
- ``service.create_run``：创建绑定场景版本 + 契约版本 + 环境快照的执行记录（QUEUED），
  不再依赖 Temporal/Worker（执行由 runner 协议 claim/heartbeat/report 完成）；
- ``mapper`` / ``completeness`` / ``snapshot_sanitizer``：展示映射、证据完整率口径、
  执行快照脱敏（证据包与版本任务执行共用）。
"""

from app.modules.execution_runtime.service import create_run  # noqa: F401
