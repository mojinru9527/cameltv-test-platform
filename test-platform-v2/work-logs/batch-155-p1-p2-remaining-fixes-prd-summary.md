# Batch 155 — P1-07 自动链路 + P2 未收口项全修复（PRD Summary）

> **Product (🟦)** | Date: 2026-08-11 | Status: Approved | Mode: full

mode: full
理由: 含新行为/新接口/新配置（失败自动链路、报告定时生成、调度停用原因字段、执行任务删除/重跑、批量生成接口），完整批次。
非目标: P3 打磨项（FIX-147-P3-*）排后续批次；知识图谱治理/空白机（已完成）；不改报告模板引擎与 Worker 引擎本体（仅加认领守卫与关联）。

## 1. 问题陈述（来源：docs/batch-147-issue-landing.md + 2026-08-11 回归）
Batch 147 审查 51 项，回归后仍余 P1-07（自动链路代码实际未合入，C147-6 被误标 Closed）与 P2 20 项（14 部分修复 + 6 未修复）：
1. **P1-07**：执行→缺陷→报告→通知自动链路 0；PR #209 只合入 docs，`auto_defect_on_fail` 仅有迁移无模型/服务/前端实现。
2. **P2-01** 计划三执行按钮并存 + 手动录入默认「通过」；**P2-02** Command Palette 泄漏；**P2-04** 安全弹窗项目名「#-」；**P2-07** 音视频流地址无 URL 校验；**P2-08** 占位页无未启用标识；**P2-09** 执行任务不可删/重跑、分组执行无安全确认；**P2-10** 接口资产缺批量生成；**P2-11** 双 Worker 竞态 + 执行双轨无关联；**P2-12** 服务层环依赖未根治；**P2-13** 交互缺口无 P0 优先；**P2-14** UI 任务 Trace 列空；**P2-15** 报告无定时生成；**P2-16** 专项测试名不副实；**P2-17** 发布包空壳缺引导；**P2-18** 调度停用无原因；**P2-19** 行操作按钮缺 aria-label；**P2-20** 用例标题不可点；**P2-21** 计划状态筛选缺「全部」；**P2-22** 集成 Test5 内网不可达；**P2-23** 知识中心 tab 全量重拉。

## 2. 成功指标
| 指标 | 基线 | 目标 |
|------|------|------|
| C147-6 自动链路代码合入 | 0（仅文档） | 模型/服务/API/前端开关全链路 + 单测 |
| 计划执行按钮 | 3 个并存 | 单一「执行」+ 范围选项；手动录入默认「请选择」 |
| 执行任务 | 不可删/重跑 | 删除/重跑入口 + 安全确认 |
| 报告定时生成 | 无 | job_type=report 定时任务 + 生成后通知 |
| Worker | 双轨无关联/可竞态 | 认领式守卫 + test_execution↔api_execution_task 关联 |
| P2 UI 体验项 | 见问题陈述 | 逐项验收标准见 PM/Design |

## 3. 用户故事 + 验收标准（摘要）
- As 测试经理, I want 计划失败自动三件套（缺陷/报告/通知）以开关控制, so that 质量闭环不依赖人工。Given 计划开启开关且一键执行有失败 / Then 自动生成缺陷（预填 case/execution）+ 报告 + plan_failed 通知；Given 未开启 / Then 零写入。
- As 测试人员, I want 计划单一执行入口 + 手动结果默认「请选择」, so that 不再误触/误存。Given 打开手动执行弹窗 / Then 结果必选后才能保存。
- As 运维, I want 调度停用填写原因, so that 停用可追溯。Given 停用调度 / Then 必填 reason 且列表展示。

## 4. 技术考量
- P1-07：模型补 `auto_defect_on_fail`（复用已入库迁移 20260811_batch151_auto_defect，模型同步字段）；service 后台任务（独立 session）→ triage(rule_only) → defect → report → notify(plan_failed)；开关默认 False。
- P2-11：Worker 认领守卫（原子 UPDATE status pending→running WHERE id=… AND status='pending'）；api_execution_task 增加 test_execution_id 关联（迁移）。
- P2-15：TestSchedule.job_type 支持 'report'（字符串字段，无迁移）；scheduler 回调调 report_service 生成项目报告 + notify。
- P2-18：TestSchedule.disabled_reason 新列（迁移）+ schema + UI 必填。
- 前端全部走 shadcn/ui + Tailwind 语义类，见 Design。

## 5. 上线计划
| 阶段 | 受众 | 成功门槛 |
|------|------|---------|
| 合入 main | 全部 | checks 全绿 + audit-ai-pr 通过 |
| 部署回归 | 测试人员 | 自动链路三件套 + P2 冒烟清单 |

## 6. 技能使用
- cameltv-bug-guard（迁移守卫/后台任务 session/React 副作用四律）
- cameltv-ui-conventions（UI 规范与无障碍）
- cameltv-agent-team 流水线
