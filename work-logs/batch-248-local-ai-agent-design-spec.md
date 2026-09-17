# Batch 248 — Design Spec

> **Design (🎨)** | Date: 2026-09-17 | Status: 就绪

## 0. 技术体系确认

shadcn/ui + Radix + Tailwind + CVA；Token 走语义类（`bg-muted` / `text-muted-foreground` / `border` / `variant`）。
参照现有实现：`src/pages/ai-config/index.tsx`、`src/pages/knowledge/components/WikiDiffDetailDrawer.tsx`（抽屉）、`src/pages/uitest/components/UiJobDetailSheet.tsx`（任务详情 Sheet）。

## 1. 组件规格表

| 组件 | 尺寸/间距 | 颜色语义 | 交互态 |
|------|-----------|---------|--------|
| 页面标题 + 说明 | `text-2xl font-semibold` + `text-sm text-muted-foreground` | 语义色 | — |
| 状态筛选（Tabs/Select） | 高 36px，`gap-2` | 选中 `bg-primary text-primary-foreground` | hover `bg-muted`；focus ring |
| Job 列表（Table） | 行高 44px，`border-b` | 状态徽标：pending=`bg-amber-100 text-amber-700`，running=`bg-blue-100 text-blue-700`，completed=`bg-emerald-100 text-emerald-700`，failed=`bg-red-100 text-red-700` | 行 hover `bg-muted/50`；点击打开抽屉 |
| 详情抽屉（Sheet） | 右侧 520px（`w-full sm:max-w-[520px]`） | — | Esc 关闭；焦点陷阱 |
| 结果 JSON 查看 | `<pre>` `max-h-80 overflow-auto rounded bg-muted p-3 text-xs` | — | — |
| 主按钮「导入用例库」 | `h-9 px-3` | `variant=default` | 进行中 disabled + Spinner |
| Agent 在线状态卡 | `rounded-md border p-3` | 在线 `text-emerald-600`，离线 `text-muted-foreground` | — |

## 2. 布局与响应式

| 断点 | 布局 | 变化 |
|------|------|------|
| ≥1024px | 双列：左侧 Job 列表（`flex-1`），右侧 Agent 状态卡（`w-72`） | 抽屉覆盖右侧 |
| 768–1023px | 单列，Agent 卡片移到底部 | 抽屉全宽 |
| <768px | 单列，表格列裁剪为「Job/类型/状态/时间」 | Sheet 全屏 |

## 3. 状态设计核对（四态）

| 组件 | Loading | Empty | Error | 未启用(503) |
|------|---------|-------|-------|-------------|
| Job 列表 | 骨架 3 行 | 「暂无 AI 任务。在需求页点击 AI 拆分，或让本地 Agent 上线后领取任务。」+ 「查看接入文档」链接 | Alert + 「重试」按钮，展示后端 `msg/detail` | 「平台内 AI 已关闭（预期行为）。请使用本地 Agent」+ 文档链接 |
| 详情抽屉 | 骨架 | 「任务详情不可用」 | Alert + `error_message` 原文 | 同上 |
| Agent 状态 | 骨架 | 「本地 Agent 离线」 | 「状态获取失败」 | — |

## 4. 设计 QA 走查发现（P0–P3，均附文件:行号）

### 🟠 P1-1 AI 配置页入口缺失（现状）
`src/pages/ai-config/index.tsx` 仅提供 provider 管理，无任何指向 AI 任务的入口 → **建议**：页头右侧新增 `Button variant=outline` 「AI 任务」跳转 `/ai-jobs`（本批实现）。

### 🟠 P1-2 需求页 AI 失败文案与"静默空结果"（现状）
`src/pages/requirement/components/AiExtractionPanel.tsx` 在 0 模块时页面上无显式失败提示 → **建议**：本批接入 Job 后，改为「已提交到本地 Agent（Job #id）」+ 轮询状态；若 `AI_PLATFORM_INFERENCE=true` 且调用失败，展示后端 `msg`。

### 🟡 P2-1 空态文案直白
AI 任务列表空态需说明"这是预期形态（平台不跑 AI）"，避免用户误判为故障（本批实现）。

## 5. 设计签核

结论：**通过**（P1-1/P1-2 在本批范围内实现；P2-1 已纳入实现；无阻断项）。
