# Batch 222 — Design Spec
> **Design (🎨)** | Date: 2026-09-05 | Status: 就绪 | Executor: Codex | 完整批次

## 0. 技术体系
`@/ui` 语义组件；Badge variant（default/destructive/outline/secondary/ghost）。

## 1. 组件规格
| 组件 | 颜色语义 | 说明 |
|------|----------|------|
| 推荐回归集卡片 | Card mt-4 | 条目 priority badge destructive/secondary + kind + source |
| 同步缺陷库按钮 | ghost | 与「转缺陷草稿」并排 |

## 2. 状态设计（四态）
推荐集空态提示；同步 toast。

## 3. 设计 QA 走查发现
### ⚪ P3-1 无效 eslint-disable
回归 effect 的 `eslint-disable-next-line` 未被使用。→ 移除。

## 4. 设计签核
结论：**通过**。
