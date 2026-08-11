# Batch 149 — Design Spec（统计口径收敛）

> **Design (🎨)** | Date: 2026-08-11 | Status: 就绪

## 0. 技术体系确认
后端 FastAPI + SQLAlchemy；前端 shadcn/ui（无新增组件，仅数据字段修复）。

## 1. 数据口径规范（本批唯一事实源 statistics_service）

| 指标 | 口径 | 备注 |
|------|------|------|
| 用例总数 | TestCase.project_id 且 is_deleted=False | 7879 |
| 计划数 | TestPlan.project_id | - |
| 执行总数 | TestExecution 经 plan_case→plan 归属项目 | 不因用例删除丢失，325 |
| 已执行用例 | distinct plan_case.case_id（is_deleted=False） | 追溯口径 |
| 已通过用例 | distinct case_id 存在 pass 执行 | 追溯口径 |
| 计划内用例 | distinct plan_case.case_id（is_deleted=False） | 覆盖率分母=用例总数 |

## 2. UI 变化
- 计划列表：`r.stats.pass_/total` 进度（前端已实现，本批仅后端补字段）。
- 工作台/追溯：展示不变，数字与统一口径一致。

## 3. 状态设计核对
| 组件 | Empty | Error |
|------|-------|-------|
| 计划列表进度 | 0/0 仅当计划确实无用例 | 保持现有错误态 |
| 工作台柱状图 | 执行 0 仅当确无执行记录 | - |

## 4. 设计走查
- P2-1：dashboard 按类型执行统计不得带 is_deleted 过滤（否则已删用例的执行记录丢失）→ 已纳入 T3。
- P2-2：追溯 by_type/by_domain 需与总数同口径 → 已纳入 T4。

## 5. 设计签核
结论：通过
