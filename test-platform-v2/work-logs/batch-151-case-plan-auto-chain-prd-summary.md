# Batch 151 — 功能用例入计划 + 失败自动转缺陷/报告/通知（PRD Summary）

> **Product (🟦)** | Date: 2026-08-11 | Status: Approved | Mode: full

mode: full
理由: 新增行为（失败自动链路 + 计划开关字段，Alembic 迁移）与 UI（用例类型筛选、开关），完整批次。
非目标: UI 自动化↔用例映射回写与批量扩量（C147-6 子项，登记 C151-1 到后续批次）；知识图谱治理/空白机（Batch 152+）；不改报告模板引擎。

## 0. 背景与来源
- 来源：`docs/batch-147-issue-landing.md` FIX-147-P1-04/07，承接 **C147-6**。
- 现状：功能用例 7845 零入计划（计划只装接口用例）；执行失败无下游动作（缺陷 0/报告 0/通知 0）；四者关联断裂。

## 1. 问题陈述
1. 计划编排 UI 无用例类型筛选，功能用例难以批量加入（后端 add_cases 本身支持任意类型）。
2. 执行失败后无自动转缺陷/生成报告/通知，质量闭环断裂（已有 triage/defect/report/notify 能力未串起来）。
3. 计划无「失败自动链路」开关，无法按计划控制是否自动写入。

## 2. 成功指标
| 指标 | 基线 | 目标 |
|------|------|------|
| 计划可添加功能用例 | 仅接口用例 | 类型筛选（全部/功能/接口/UI）+ 徽标 |
| 失败自动转缺陷 | 0 | 开关开启时，失败执行自动生成缺陷（预填 case/execution） |
| 失败自动生成报告 | 0 | 开关开启时失败计划自动生成报告 |
| 失败自动通知 | 0 | plan_failed 事件推送（webhook/email） |
| 四者关联 | 断裂 | 缺陷↔执行↔用例预填；计划详情展示用例类型分布（需求→用例→执行→缺陷 已由既有字段贯通） |

## 3. 用户故事 + 验收标准
- As 测试人员, I want 计划编排时按类型筛选并添加功能用例, so that 功能用例也能纳入计划执行。
- As 测试经理, I want 失败执行自动转缺陷/生成报告/通知, so that 质量闭环不依赖人工。
  - Given 计划开启「失败自动链路」且执行有失败 / When 一键执行完成 / Then 自动生成缺陷（关联 case_id/execution_id）+ 报告 + plan_failed 通知。
  - Given 计划未开启 / Then 不产生任何自动写入。

## 4. 技术考量
- TestPlan 增加 `auto_defect_on_fail: bool = False`（Alembic 迁移，幂等）。
- 自动链路（后台任务、独立 session）：triage(rule_only) → 对 bug/case_defect 生成缺陷草稿 → defect_service.create_defect → report_service.create_report（无模板）→ notify_sync("plan_failed")。
- 通知模板新增 plan_failed；事件列表支持。
- 前端：AddCasesModal 加 case_type 筛选 + 类型徽标；PlanDrawer 加开关（Checkbox）。
- 风险：自动写入需开关兜底（默认关）；后台任务独立 session 防事务污染；测试直接调用 service 层验证（避开真实 SessionLocal）。

## 5. 上线计划
| 阶段 | 受众 | 成功门槛 |
|------|------|---------|
| 合入 main | 全部 | checks 全绿 |
| 部署回归 | 测试人员 | 开关开启→失败自动三件套 |

## 6. 技能使用
- cameltv-bug-guard（迁移守卫、后台任务 session 隔离）
- cameltv-agent-team 流水线
