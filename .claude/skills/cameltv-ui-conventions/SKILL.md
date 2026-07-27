---
name: cameltv-ui-conventions
description: test-platform-v2 前端 UI 规范——用哪个组件、什么样式基线、以及历史上反复返工五六次的显示/样式问题红旗清单。Use when building or reviewing any test-platform-v2/frontend page or component, doing 设计走查, or when the user mentions "组件显示/样式/深色模式/徽标颜色/状态标签/响应式/间距/加载态/空态". Triggers: "改 UI", "组件样式", "设计还原", "ui conventions", "为什么这个显示不对".
---

# CamelTv 前端 UI 规范

> 目的：把设计/前端反复返工的显示与样式问题固化成规范，一次做对。

## 技术栈（先纠正一个长期误解）

真实栈是 **shadcn/ui（Radix primitives + Tailwind CSS + CVA）**，**不是 Ant Design**。旧 memory/文档里「基于 Ant Design 5」已过时，以真实代码为准（见 `test-platform-v2/CLAUDE.md` ADR-0006）。

- 颜色/尺寸走 **Tailwind 语义类**：`bg-background` `bg-card` `bg-muted` `text-foreground` `text-muted-foreground` `border` `text-destructive` + Button/Badge 的 `variant` 系统。**别用 AntD Token，别用裸色阶**（`bg-blue-50`…，除非按 RECIPES 补齐 `dark:` 变体）。
- 主题由 `data-theme-id` 驱动（crystal/xlab/column/clay/liquid）+ `.dark` class，全部定义在 `src/globals.css`。**改颜色改 CSS 变量，不在组件里写死颜色。**
- 无 Markdown 渲染库：长文本/JSON 用 `<pre className="whitespace-pre-wrap">` 直出。

## 用哪个组件（先复用，别造轮子）

| 需求 | 用这个 | 位置 |
|------|--------|------|
| 列表页 加载/错误/空/数据 四态 | `AsyncState`（render-prop 包裹） | `components/state/AsyncState.tsx` |
| 表格（主内容是表） | `DataTable`（内联 loading/error/select） | `components/DataTable.tsx` |
| 单独 加载/错误/空 | `LoadingState` / `ErrorState` / `EmptyState` | `components/state/`、`components/EmptyState.tsx` |
| 页头（标题+操作区） | `PageHeader` | `components/PageHeader.tsx` |
| 指标卡 | `StatCard` | `components/StatCard.tsx` |
| 搜索 / 分页 | `SearchInput` / `Pagination` | `components/` |
| 基础控件 | `components/ui/*`（button/card/badge/select/dialog/sheet/tabs/switch/input/textarea/skeleton/tooltip…） | shadcn 生成 |

⚠️ `components/ui/*` 是 shadcn 生成物，**不手改**（升级会被覆盖）；要变体去改调用处的 className 或 `globals.css`。

## 样式基线（与知识中心/SearchTab 对齐，别引入新视觉语言）

| 维度 | 约定 |
|------|------|
| 容器间距 | 外层 `space-y-3` / `space-y-4` |
| 卡片 | `Card > CardContent p-3` 或 `p-4` |
| 工具条 | `flex items-center gap-2`，主按钮 `ml-auto` 靠右 |
| 控件高度 | 检索区 `h-9`；卡内小控件 `h-7`/`h-8` |
| 次要文字 | `text-xs` / `text-[11px] text-muted-foreground` |
| 图标 | Lucide，`size-4`（Tab 图标 `size-4 mr-1`） |
| 加载 | `Loader2 animate-spin` + `Skeleton` |
| 反馈 | `sonner` toast |
| 焦点 | 全局 `*:focus-visible` ring（globals.css），无需逐组件加 |

## Red Flags — 历史反复返工的 8 类问题（改前逐条自检）

1. **严重级 Badge 颜色不可辨**：P0 与 P1 不能同色。用四级可辨梯度（P0 实心红 / P1 橙描边 / P2 灰 / P3 描边），共享助手 `wikiSeverity.ts::severityBadge()`。见 [RECIPES.md](RECIPES.md) §1。
2. **硬编码语义色没深色变体**：`bg-blue-50 text-blue-700` 这类在深色模式浅底刺眼且对比度 < WCAG AA。必须补 `dark:` 变体或抽 `info/success/warning` 语义 Token。见 RECIPES §2。
3. **状态标签裸英文**：`approved/pending/failed/active` 直接渲染后端枚举，与全中文界面割裂。补中文映射字典（`REVIEW_STATUS_LABEL`/`TASK_STATUS_LABEL`），与 `PAGE_TYPE_LABEL` 同风格。见 RECIPES §3。
4. **缺 Error 态 / 四态不全**：`load().catch(()=>null)` 把接口失败静默当空，用户分不清「加载失败」和「真没数据」。列表页四态（Loading/Empty/Error/未启用503）齐备，优先用 `AsyncState`/`DataTable`。见 RECIPES §4。
5. **失败态误用加载动画**：`status!=='success'` 一律转圈 + "任务 failed…"，让已失败的任务看起来还在跑。拆 `running`（spin）与 `failed`（`AlertCircle` 红 + 重试按钮）两态。
6. **原始 JSON 裸展示**：`font-mono break-all` 直出转义串对非技术用户不可读。先 `JSON.parse` 再 `JSON.stringify(x,null,2)` 放 `<pre>`（含解析失败兜底）。见 RECIPES §5。
7. **触控目标 < 44px**：树节点 `px-2 py-1`（约 28px）、`h-6`/`h-7` 行内动作，触屏误触。列表主点击区 `min-h-[36px]`、行内动作升 `h-8`。
8. **响应式断点跨度过大 / Tab 溢出**：`grid grid-cols-1 lg:grid-cols-[...]` 从 1 栏直跳 3 栏，丢失并排对照语义；缺 `md:` 中间态。多 Tab（9 个）在平板 768px 挤压溢出。窄屏用 `Tabs` 切换保留对照心智；补 `md:` 过渡。

## 无障碍（WCAG 2.1 AA，硬指标）

- 表单控件 `<label htmlFor>` 或 `aria-label`；图标按钮 `aria-label`；纯图标关闭键加 `<span className="sr-only">`。
- 复合 `button`（多 Badge + 截断标题）加汇总 `aria-label`；筛选 `Select` 加 `aria-label`；`truncate` 标题加 `title`。
- 正文对比度 ≥ 4.5:1，大文字 ≥ 3:1；高对比 Token：`--text-muted-high-contrast` → `text-muted-hc`，`--border-high-contrast` → `border-hc`。
- 自检：`npm run dev` 后 `npx @axe-core/cli --stdout http://localhost:5173/<page>` 或 axe DevTools；CI 门禁 Lighthouse a11y ≥ 90。演示态页（apitest/uitest/special）豁免。

## 关联

- [RECIPES.md](RECIPES.md) — 可复制的配色/状态映射/四态/JSON/响应式代码 + 设计 Token 速查
- `cameltv-agent-team` skill（Design 部门走查）、`cameltv-bug-guard` skill（前端铁律）
- 真实源：`src/globals.css`、`components/ui/badge.tsx`、`components/state/AsyncState.tsx`、`pages/knowledge/components/wikiSeverity.ts`
