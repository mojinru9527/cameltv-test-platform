# Batch 218 — Design Spec
> **Design (🎨)** | Date: 2026-09-03 | Status: 就绪 | Executor: Codex | 完整批次

## 0. 技术体系确认
前端 `@/ui` 语义组件；后端 FastAPI + SQLAlchemy。语义 token（batch54）约束：不用固定色板。Badge 使用 `variant`（default/destructive/outline/secondary/ghost）或 `tone`（success/warning/danger/info/neutral）。

## 1. 组件规格表
| 组件 | 尺寸/间距 | 颜色语义 | 交互态 |
|------|-----------|----------|--------|
| 一键运行按钮 | md | primary | loading disabled |
| 覆盖率 Badge | sm | secondary/destructive | — |
| 失败条目 | border p-2 | kind badge destructive + title | hover |
| 证据回放行 | text-xs | status badge secondary/destructive | 链接查看 |

## 2. 布局与响应式
单列详情卡片；进度条 + 覆盖行 + 失败分类 + 证据回放分段展示；`<1024px` 仍单列。

## 3. 状态设计核对（四态）
| 场景 | Loading | Empty | Error | 未启用 |
|------|---------|-------|-------|--------|
| 运行 | progress 0-100 | 无已采纳方案条目 | toast.error | 任务未 approved/executing 时拒跑 |

## 4. 设计 QA 走查发现（P0–P3）
### ⚪ P3-1 Badge 语义
首版用 `variant="danger"`（Badge 无该 variant，是 tone）。→ **已改 `variant="destructive"`**。

## 5. 设计签核
结论：**通过**（执行与证据页消费 version_task_run 事实源；失败四分类 + 缺陷草稿；无固定色板）。
