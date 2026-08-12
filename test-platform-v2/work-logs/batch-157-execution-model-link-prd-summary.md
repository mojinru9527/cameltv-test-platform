# Batch 157 — 执行模型双向关联（test_execution ↔ api_execution_task）

> **Product (🟦)** | Date: 2026-08-12 | Status: Approved | Mode: full

mode: full
理由: 架构重构/新字段（两表新增关联列 + 计划执行登记 API 任务快照），引入新行为，完整批次。
非目标: 不合并两表（保留各自职责）；不改变同步执行语义（计划执行仍即时返回）；不改变 apitest 独立任务语义。

## 1. 问题陈述
Batch 147 P2-11「执行双轨」遗留：同一 API 用例可从两条入口执行，结果分别落在 `test_execution`（计划）与 `api_execution_task_item`（接口测试），两表无任何关联：
- 计划执行历史看不到请求/响应/断言结构化快照（仅 actual_result JSON 文本）；
- 接口测试任务无法追溯到对应计划执行；
- 统计与排障需在两套模型间人工对账。

## 2. 成功指标
| 指标 | 基线 | 目标 |
|------|------|------|
| 计划 API 执行 → API 任务快照 | 无 | 每次计划批量/自动执行 API 生成 1 个 trigger_type=plan 任务 + 每条 item 双向关联 |
| TestExecution.api_task_id | 无 | 计划 API 执行行可反查任务 |
| ApiTaskItem.test_execution_id | 无 | 任务明细可反查计划执行 |
| 既有行为 | - | 同步执行、计划统计、worker 认领不受影响 |

## 3. 用户故事 + 验收标准
- As 测试人员, I want 计划 API 执行在接口测试任务列表看到结构化快照, so that 排障无需解析 JSON 文本。
- As 测试人员, I want 任务明细看到关联计划执行, so that 两条入口可互相追溯。
  - Given 计划批量执行包含 API 用例 / When 执行完成 / Then 生成 trigger_type=plan 任务（status=success），item.test_execution_id=执行记录 id，execution.api_task_id=任务 id。
  - Given apitest 独立任务 / When 执行完成 / Then 无 test_execution_id（保持独立语义）。

## 4. 技术考量
- 迁移 `20260812_batch157_exec_link`：test_execution.api_task_id、api_execution_task_item.test_execution_id（nullable FK，幂等）。
- test_plan_service：execute_all_cases / auto_execute_api_cases 内为 API 用例登记任务+快照（request/response/assertions），exec_row flush 后回填 api_task_id。
- 不经过 worker（同步完成直接 status=success），避免计划执行语义变化。
- 前端：计划执行历史「API 任务」列 + 任务明细「关联计划执行」。

## 5. 上线计划
| 阶段 | 受众 | 成功门槛 |
|------|------|---------|
| 合入 main | 全部 | checks 全绿 |
| 部署回归 | 测试人员 | 计划执行→任务快照→双向追溯冒烟 |

## 6. 技能使用
- cameltv-bug-guard（迁移守卫/批量写入）
- cameltv-agent-team 流水线
