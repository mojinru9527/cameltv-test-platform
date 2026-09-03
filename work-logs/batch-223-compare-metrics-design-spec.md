# Batch 223 — Design Spec
> **Design (🎨)** | Date: 2026-09-03 | Status: 就绪 | Executor: Codex | 完整批次

## 0. 技术体系
前端 `@/ui` 语义组件；后端派生指标。

## 1. 组件规格
| 组件 | 颜色语义 | 说明 |
|------|----------|------|
| 指标卡片 | Card | 4 张（人天/周期/漏测/周活跃），value 大字 |
| 对比表单 | Input + Button primary | 版本 A/B + 对比 |

## 2. 状态设计（四态）
对比空态提示；指标加载空态显示 0。

## 3. 设计 QA 走查发现
### ⚪ P3-1 路由顺序
`/version-tasks/compare` 被 `/{task_id}` 吞掉造成 422。→ 移到 /{task_id} 前声明。

## 4. 设计签核
结论：**通过**。
