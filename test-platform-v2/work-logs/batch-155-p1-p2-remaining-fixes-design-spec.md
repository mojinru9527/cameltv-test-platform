# Batch 155 — Design Spec（P1-07 自动链路 + P2 UI 打磨）

> **Design (🎨)** | Date: 2026-08-11 | Status: 就绪

## 0. 技术体系确认
shadcn/ui + Radix + Tailwind + CVA；Token 走语义类；真实栈非 Ant Design。

## 1. 组件规格表
| 组件 | 规格 |
|------|------|
| PlanDetail 执行弹窗 | Dialog「执行计划」：范围 Select（全部用例/仅 API 用例）+ 环境 Select（API 范围时）+ 确认按钮；替换顶部「批量执行/一键执行」两按钮 |
| 手动执行结果 Select | 默认 placeholder「请选择」，空值禁用保存 |
| 自动链路开关 | Checkbox + label「失败自动转缺陷/报告/通知（默认关闭）」 |
| 执行任务行操作 | 重跑（ghost icon + aria-label）、删除（danger icon + AlertDialog 确认） |
| 批量生成用例 | 服务行「生成全部用例」按钮 + 结果 toast |
| 调度停用原因 | 停用弹窗必填 Textarea；列表「停用原因」列 |
| 知识中心 Tabs | 已访问 tab forceMount 保持状态，避免切页重拉 |

## 2. 状态设计核对
| 组件 | Loading | Empty | Error | 未启用 |
|------|---------|-------|-------|--------|
| 执行任务 | DataTable 四态 | EmptyState | ErrorState | - |
| 占位页（SoloX/运维/组织） | - | - | - | Badge「功能未启用」+ 说明 |
| 接口资产批量生成 | 按钮 loading | - | toast | - |

## 3. 无障碍
- 所有 icon-only 行操作补 aria-label（special/defect/report/notify/uitest/task）
- CommandPalette 关闭态不渲染 Dialog 内容（不入 ARIA 树）
- 用例标题点击区 ≥36px、加 title

## 4. 设计签核
结论：通过（P2 项走查按 cameltv-ui-conventions Red Flags 逐条）
