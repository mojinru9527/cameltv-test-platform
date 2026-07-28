# Batch 38 — Design Spec
> **Design (🎨)** | Date: 2026-07-23 | Status: 就绪

## 0. 技术体系确认
shadcn/ui + Radix + Tailwind + CVA；Token 走语义类（bg-muted / text-muted-foreground / border / variant）。

## 1. 组件规格表

### 1.1 检索结果卡片（SearchTab）— 新增交互

| 组件 | 尺寸/间距 | 颜色语义 | 交互态 |
|------|----------|---------|--------|
| Card（结果条目） | px-3 py-2 → 增加 cursor-pointer hover:border-primary/30 | 默认 border，hover 变 border-primary/30 | 默认/hover/点击打开弹窗 |
| Dialog（详情） | max-w-6xl max-h-[90vh] overflow-y-auto | 标准 Dialog 样式 | 打开/ESC关闭/遮罩关闭 |

**改动点**：当前 Card 无 onClick，需添加点击处理和 Dialog 组件。

### 1.2 知识源详情弹窗（ProjectTab/PlatformTab/SourceListTab）— 尺寸修正

| 组件 | 当前值 | 修正值 | 理由 |
|------|--------|--------|------|
| DialogContent max-w | `max-w-5xl` (1024px) | `max-w-7xl` (1280px) | 长 raw_content/chunk 内容需更大空间 |
| DialogContent max-h | `max-h-[92vh]` | `max-h-[90vh]` | 保持，但确保 overflow-y-auto |
| DialogContent width | `w-[95vw]` | `w-[95vw]` | 保持，小屏适配 |
| `<pre>` 内容区 | `max-h-96` (384px) | `max-h-[60vh]` | 大弹窗应允许更高内容区 |

### 1.3 验证按钮状态（SourceListTab/PlatformTab）— 状态反馈

| 状态 | 图标 | 颜色 | 交互 |
|------|------|------|------|
| 未验证 | `CheckCircle2` outline | text-muted-foreground | 可点击 |
| 验证中 | `Loader2` spin | text-muted-foreground | disabled |
| 已验证（本次操作后） | `CheckCircle2` filled | text-green-600 | disabled（已验） |
| 已验证（历史） | `CheckCircle2` filled | text-green-500 | disabled |

**实现方式**：
- PlatformTab 已有用 `verifyKnowledgeSource` 返回值更新本地 state 的逻辑（L67-70），验证后 freshness_score=1.0 + last_verified_at 更新 → 刷新列表即可
- SourceListTab 当前用 `await verifyKnowledgeSource(sourceId)` 忽略返回值后 `load()` 重载，需改为用返回值更新 `rows` state 中的对应项，**同时**将按钮变为绿色已验态

## 2. 布局与响应式

| 断点 | 布局变化 |
|------|---------|
| < 768px (mobile) | 弹窗全屏 `w-[100vw] h-[100dvh] max-w-none max-h-none rounded-none` |
| 768-1024px (tablet) | 弹窗 `max-w-3xl w-[90vw]` |
| ≥ 1024px (desktop) | 弹窗 `max-w-7xl w-[85vw]` |

## 3. 状态设计核对（四态）

| 组件 | Loading | Empty | Error | 未启用(503) |
|------|---------|-------|-------|------------|
| SearchTab 结果弹窗 | Loader2 居中 | "暂无内容" | toast 错误 | N/A（前端错误兜底） |
| 验证按钮 | Loader2 spin | N/A | toast "验证失败" | N/A |
| 向量回填按钮 | Loader2 + "回填中…" | N/A | toast 错误详情 | **已修复**：默认启用，不再 503 |
| 图谱提取/演化 | Loader2 | "请先选择实体" | toast 错误 | **已修复**：默认启用 |
| 蓝湖采集 | Loader2 进度 | "暂无任务" | toast 错误详情 | **已修复**：默认启用 |

## 4. 设计 QA 走查发现（基于现有代码审查）

### 🔴 P0-1: 检索结果卡片无点击响应
[SearchTab.tsx:236-252](test-platform-v2/frontend/src/pages/knowledge/components/SearchTab.tsx#L236-L252) — Card 组件缺少 onClick handler → **修复**：添加 onClick + Dialog

### 🔴 P0-2: 验证按钮操作无即时视觉反馈
[SourceListTab.tsx:90-106](test-platform-v2/frontend/src/pages/knowledge/components/SourceListTab.tsx#L90-L106) — `handleVerify` 调用 `await verifyKnowledgeSource(sourceId)` 忽略返回值，只靠 `load()` 重载 → **修复**：用返回值更新 rows state

### 🟠 P1-1: 弹窗预格式化文本可能溢出
[ProjectTab.tsx:212](test-platform-v2/frontend/src/pages/knowledge/components/ProjectTab.tsx#L212) — `<pre>` 块 `max-h-[500px]` 在大弹窗中限制了可见内容 → **修复**：改为 `max-h-[60vh]`

### 🟡 P2-1: 弹窗 max-w-5xl 对大文本仍不足
[PlatformTab.tsx:208](test-platform-v2/frontend/src/pages/knowledge/components/PlatformTab.tsx#L208) — `max-w-5xl` = 64rem = 1024px，对于宽屏仍显局促 → **修复**：改为 `max-w-7xl`（1280px）

## 5. 设计签核
结论：通过 — 所有修改为现有组件的参数调整和交互补全，不引入新组件范式。
