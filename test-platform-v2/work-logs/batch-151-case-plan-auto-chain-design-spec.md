# Batch 151 — Design Spec（功能用例入计划 + 失败自动链路）

> **Design (🎨)** | Date: 2026-08-11 | Status: 就绪

## 0. 技术体系确认
shadcn/ui + Radix + Tailwind；后端 FastAPI + SQLAlchemy。

## 1. UI 变更
| 组件 | 规格 |
|------|------|
| AddCasesModal 类型筛选 Select | 全部/功能/接口/UI，w-[110px]，默认全部；变更后重置分页并重查 |
| 用例类型徽标 | manual=功能(neutral)、api=接口(accent)、ui=UI(orange) |
| PlanDrawer 开关 | Checkbox + label「失败自动转缺陷/报告/通知」，默认关闭 |

## 2. 状态核对
| 组件 | 默认 | 开启 |
|------|------|------|
| 自动链路 | 不产生任何写入 | 缺陷+报告+通知 |
| 通知 | - | plan_failed 模板 |

## 3. 数据流
执行完成(execute-all/auto-execute) → failed>0 且 auto_defect_on_fail → 后台任务：
triage(rule) → 缺陷(预填 case/execution) → 报告 → plan_failed 通知

## 4. 设计签核
结论：通过
