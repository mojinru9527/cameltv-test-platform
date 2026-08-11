# Batch 149 — 统计口径收敛 + 计划列表进度 0/0（PRD Summary）

> **Product (🟦)** | Date: 2026-08-11 | Status: Approved | Mode: full

mode: full
理由: 统计服务重构（5 套口径收敛 1 套）+ 新响应字段（PlanOut.stats），属重构/新行为，按 SKILL.md 判定完整批次。
非目标: 请求缓存/防抖/mindmap 聚合（Batch 150）、功能用例入计划与失败自动链路（Batch 151）、文档/图谱/空白机（Batch 152+）、需求覆盖率与 AI 置信度（C126-2/C126-3）不在本批；本批不改报告模板内容、不动 ApiExecutionTask 域（其口径为「任务/运行数」，与用例域口径分开文档化）。

## 0. 背景与来源

- 来源：`docs/batch-147-issue-landing.md` FIX-147-P1-01/02，承接 **C147-3 / C147-4**（并承接 C146-2）。
- 现状矛盾（生产 2026-08-11）：工作台用例 7879 / 执行 0；追溯用例 9429 / 已执行 325；计划 325；dashboard 执行计数与 test_execution 表 325 矛盾；计划列表进度恒 0/0。

## 1. 问题陈述

1. **口径分裂**：dashboard_service（is_deleted=False，7879）、trace_service（未过滤 is_deleted，9429）、test_plan_service（plan_case last_status，325）、report_service、report_aggregator（任务域）各写一套查询。
2. **dashboard 执行计数 0**：按类型执行统计的关联子查询带 `is_deleted=False`，执行记录若挂在已删除用例的 plan_case 上被过滤 → 与 test_execution 表 325 矛盾。
3. **追溯总数虚高**：`trace_service.get_project_coverage` 的 total_cases/by_type/by_domain 未过滤 is_deleted → 9429 vs 实际 7879。
4. **计划列表 0/0**：`list_plans` 已计算 stats，但 `PlanOut` schema 未声明 `stats` 被 Pydantic 丢弃，前端读不到。

## 2. 成功指标

| 指标 | 基线 | 目标 | 测量窗口 |
|------|------|------|---------|
| 用例总数（工作台/追溯） | 7879 vs 9429 | 两端一致（is_deleted=False） | 同一 SQLite/生产查询 |
| dashboard 执行计数 | 0 | = test_execution 行数（325） | 接口返回 |
| 追溯已执行/已通过 | 325 | 与 test_execution 一致 | 接口返回 |
| 计划列表进度 | 0/0 | 显示 pass_/total | 接口 + UI |
| 统计实现 | 5 套 | 用例域收敛 1 套 statistics_service | 代码引用 |

## 3. 用户故事 + 验收标准

- As 测试经理, I want 工作台/追溯/计划的用例数与执行数一致, so that 决策不被矛盾数字误导。
  - Given 项目有 7879 有效用例 / 325 执行记录 / When 打开工作台、追溯、计划列表 / Then 三处「用例总数」一致且「执行」>0。
- As 测试经理, I want 计划列表直接看到每条计划的进度, so that 无需进入详情。
  - Given 计划有 10 用例 3 通过 / When 查看计划列表 / Then 进度显示 3/10。

## 4. 技术考量

- 新建 `app/services/statistics_service.py` 作为用例域唯一统计源：
  - total_cases / api_cases / total_plans（is_deleted=False）
  - execution_total/pass/fail（TestExecution 经 plan_case→plan 归属项目，不因用例删除而丢失）
  - cases_in_plans / cases_executed / cases_passed（去重用例级）
  - by_type（manual/api/ui）分类型 count + execution 计数
- dashboard_service / trace_service 改为调用 statistics_service；trace 的 by_domain 单独保留但补 is_deleted。
- report_aggregator 属「执行任务/运行」域，不改口径，在 docstring 标注边界。
- `PlanOut` 增加 `stats: PlanStats`；前端计划列表已读 `r.stats`，无需改前端逻辑。
- 风险：is_deleted 过滤可能与历史执行归属冲突 → 执行计数不因用例删除而过滤（保留真实执行），仅「用例总数/类型分布」过滤。
- 依赖：无新增。

## 5. 上线计划
| 阶段 | 受众 | 成功门槛 |
|------|------|---------|
| 合入 main | 全部 | checks 全绿 + 审计 |
| 部署回归 | 测试经理 | 三端数字一致 + 计划进度可见 |

## 6. 技能使用
- cameltv-bug-guard → 批量查询/N+1、schema 字段同步核对
- cameltv-agent-team 流水线 → 本批工件
