# Batch 157 — Design Spec（执行模型双向关联）

> **Design (🎨)** | Date: 2026-08-12 | Status: 就绪

## 0. 技术体系确认
FastAPI + SQLAlchemy；前端 shadcn/ui + Tailwind。

## 1. 数据模型
| 表 | 新增列 | 语义 |
|----|--------|------|
| test_execution | api_task_id (nullable FK) | 计划 API 执行 → 对应 API 任务 |
| api_execution_task_item | test_execution_id (nullable FK) | 任务明细 → 计划执行记录 |

## 2. UI 变更
| 组件 | 规格 |
|------|------|
| PlanDetail 执行历史 | 新增「API 任务」列：api_task_id 存在时 Badge「API 任务 #id」+ title 说明；空显示 - |
| TaskTab 明细 | item.test_execution_id 存在时显示「关联计划执行 #id」小字 |

## 3. 状态核对
| 场景 | 结果 |
|------|------|
| 计划批量/自动执行（含 API） | 同步完成 + 1 个 plan 任务 + N 个 item 双向关联 |
| apitest 独立任务 | 无 test_execution_id（保持独立） |
| 手动执行用例 | 不生成 API 任务（无快照来源） |

## 4. 设计签核
结论：通过
