# Batch 186 — PRD：遗留收口（C182-1 单一事实源 / C182-2 回填验证 / C184-1 沙箱评估）

> **mode: full**（重构 + 交付物），六部门工件
> 来源：C-CONDITIONS C182-1（P2）/ C182-2（P3）/ C184-1（P3）
> 执行：DeepSeek Harness（direct）| 日期：2026-08-16

---

## 1. 问题陈述

三项遗留条件：

1. **C182-1 执行记录双写（P2）**：计划 API 执行同时写 `test_execution` 与 `api_execution_task_item`（+ `api_execution_task` trigger_type=plan），
   同一执行事实两份记录 + 双向互指（`test_execution.api_task_id` ↔ `item.test_execution_id`）。
   Batch 175 已定统计口径为 test_execution（用例级）；双写仅服务于「接口测试任务页展示计划任务」这一副 UI 用途，
   且聚合层（report_aggregator/statistics）均不读 trigger_type=plan 任务 → **双写为纯冗余写入**。
2. **C182-2 域命名回填（P3）**：`scripts/backfill-domain-naming-b182.py` 已交付但未验证（无测试、无本地 dry-run 证据、无生产执行手册）。
3. **C184-1 OS 级沙箱评估（P3）**：Batch 184 进程内隔离已落地；OS 级沙箱（seccomp/nsjail）是否需要、何时需要的**评估结论**未成文。

## 2. 成功指标

| 指标 | 目标 |
|------|------|
| C182-1 | 计划执行**不再创建** api_execution_task/items（唯一事实源=test_execution）；历史 plan 任务保留可读；统计/报告/追溯口径不变；计划执行链路测试全绿 |
| C182-2 | 回填脚本单测（映射/dry-run/apply 幂等）全绿；本地 dry-run 证据；生产执行手册（脚本 docstring + deploy 文档）；条件转 Deferred（生产人工执行，解除条件=生产窗口） |
| C184-1 | `docs/adr/0020` 评估结论成文（Railway 容器隔离=当前部署形态充分；自托管裸机需补 seccomp/nsjail → deploy 手册条款）；条件关闭 |
| 全量 | 后端 pytest 无新增失败；ruff/alembic 门禁绿 |

## 3. 验收

- Given 计划含 API 用例，When execute-all/auto-execute，Then 仅 test_execution 落库（api_execution_task 数量不变、无 trigger_type=plan 新行、无 api_task_id 互指）。
- Given 历史 plan 任务（存量），When 接口测试任务列表查询，Then 仍正常返回（可读、含 items）。
- Given 统计/报告/追溯查询，When 计划执行后，Then 结果与双写时代一致（口径不变）。
- Given 回填脚本，When dry-run/apply 单测执行，Then 映射正确、幂等、本地 dry-run 输出统计。
- Given 沙箱评估 ADR，When 审阅，Then 结论与部署形态对应、自托管裸机触发条件明确。

## 4. 非目标

- 生产库 plan 历史任务清理（保留可读；清理属运维，手册注明可选步骤）。
- `test_execution.api_task_id` / `item.test_execution_id` 列删除（保留历史链接，仅不再写入）。
- C182-2 生产 `--apply`（外部人工操作，条件转 Deferred）。
- 其他 Open 条件（C95-x/C111-x 等外部项）。

## 5. C 条件

- C75-1 mode:full ✅；C75-3/C76-2/C78-1/C86-1/C104-5 ✅
- 关闭：C182-1（附 commit + 测试证据）、C184-1（附 ADR）
- 转 Deferred：C182-2（解除条件=生产窗口人工执行，手册/脚本测试已交付）

## 6. 风险

| 风险 | 缓解 |
|------|------|
| 移除双写影响接口任务页展示 | 仅停止**新建** plan 任务；历史任务保留；手动批量任务（trigger_type=manual/retry_failed）完全不受影响 |
| 计划执行测试断言旧行为 | 更新 test_batch169_plan_async 等改为断言 test_execution 完整性 |
| 聚合口径回归 | statistics/report/trace 相关测试全量回归（batch-175 口径不变） |
