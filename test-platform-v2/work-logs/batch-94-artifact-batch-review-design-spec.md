# Batch 94 — Design Spec（AI 产物批量审核/采纳 UI）

> **Design (🎨)** | Date: 2026-08-05 | Status: 就绪

## 0. 技术体系确认

shadcn/ui + Tailwind 语义类；复用 ArtifactReviewTab 现有表格/弹窗体系；Checkbox 用 `@/components/ui/checkbox`。

## 1. 组件规格表

| 组件 | 规格 | 交互 |
|------|------|------|
| 行勾选 Checkbox | `w-10` 列，仅 pending/approved 行可勾 | onCheckedChange 切换 selectedIds |
| 全选 Checkbox | 表头列，当前页可操作行全选/取消 | checked=全部选中；indeterminate 由 Radix 处理 |
| 批量按钮组 | 工具栏右侧（ml-auto）：批量采纳（secondary）/批量驳回（secondary）/批量导入（primary） | 有选中才显示；min-h-9 |
| 批量 Dialog | max-w-md：采纳（意见可选）/驳回（原因必填）/导入（治理提示） | 确认 → loading → toast 计数 |

## 2. 状态设计（四态）

| 组件 | Loading | Empty | Error | 无选中 |
|------|---------|-------|-------|--------|
| 批量按钮组 | — | — | — | 隐藏（选中>0 才显示） |
| 批量导入 | 提交中 spinner | — | toast 错误（含 403 治理提示） | 禁用 |

## 3. 设计 QA 走查发现

### ⚪ P3-01 全选语义
全选勾选「当前页可操作」行（pending+approved），跨状态行的勾选由用户自行处理；批量导入仅 approved 生效（后端守卫兜底）——文档化该语义，避免误解。

## 4. 设计签核

结论：**通过**。
