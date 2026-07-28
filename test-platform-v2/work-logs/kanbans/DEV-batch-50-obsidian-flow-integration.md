# DEV Kanban — batch-50-obsidian-flow-integration

> **Dev (💻)** | Date: 2026-07-28 | Status: 🔄 In Progress

## 当前位置

| Slice | 状态 | 内容 |
|-------|------|------|
| Slice 1 | 🔄 编码 | CSS类 + Badge替换 (低风险高收益) |
| Slice 2 | ⏳ 待开始 | Button 替换 + MetricStrip / SpatialChain 接入 |
| Slice 3 | ⏳ 待开始 | Environment + 其他未接入页面 ObsidianFlow 化 |
| Slice 4 | ⏳ 待开始 | PageShell 统一页面框架 |

## Slice 1: CSS 类强化 + Badge 替换

**方案**: 不改 import，先加 CSS 类
- 所有 `<Card>` → 加 `className="ui-surface"` 
- 所有 `<Table>` → 加 `className="ui-table"`
- MainLayout 侧边栏 → 替换内联 `<style>` 为 `ui-glass` 类
- 所有页面 Badge import 从 shadcn 切到 `@/ui`
  - `variant="destructive"` → `tone="danger"`
  - `variant="secondary"` → `tone="warning"`
  - `variant="default"` → `tone="neutral"`
  - `variant="outline"` → `tone="neutral"`

### 涉及文件
- `frontend/src/pages/testcase/index.tsx` — Card + Table + Badge (P0-P3优先级 + 评审状态)
- `frontend/src/pages/testplan/index.tsx` — Card + Table + Badge
- `frontend/src/pages/requirement/index.tsx` — Card + Badge
- `frontend/src/pages/defect/index.tsx` — Card + Badge (子组件 DefectTable, DefectStatsCards)
- `frontend/src/pages/report/index.tsx` — Card + Table + Badge
- `frontend/src/pages/trace/index.tsx` — Card + Badge
- `frontend/src/layouts/MainLayout.tsx` — 侧边栏 ui-glass

## Slice 2: Button 替换 + 语义组件

**方案**: 替换 Button import 到 `@/ui`，用 Tailwind class 补偿 size
- `@/ui` Button 无 `size` prop，需手动加 class：
  - `size="sm"` → `className="text-xs px-3 py-1 min-h-0"`
  - `size="icon-xs"` → `className="size-7 min-h-0 p-0"`
- 语义组件接入：
  - Workbench: 顶部 `<MetricStrip metrics={...} />`
  - Trace: 底部/中间 `<SpatialChain nodes={...} />`
  - Defect: 缺陷等级用 `<StatusBadge variant={...} />`

### 涉及文件
- `frontend/src/pages/workbench/index.tsx` — MetricStrip
- `frontend/src/pages/trace/index.tsx` — SpatialChain
- `frontend/src/pages/defect/DefectTable.tsx` — StatusBadge
- 7 个页面 Button import 替换

## Slice 3: Environment + 未接入页面

**方案**: 
- Environment 页面接入 `useObsidianPage` + ObsidianListPage
- ApiTest, UiTest, Schedule 等至少 5 个核心页面接入

### 涉及文件
- `frontend/src/pages/environment/index.tsx` — 优先
- `frontend/src/pages/apitest/index.tsx`
- `frontend/src/pages/uitest/index.tsx`
- `frontend/src/pages/schedule/index.tsx`
- `frontend/src/pages/system/index.tsx`

## Slice 4: PageShell 统一

**方案**: 页面自定义 PageHeader → PageShell 组件

### 涉及文件
- 至少 5 个列表页 — 替换 `<PageHeader>` → `<PageShell>`

---

## 批次记录

| 批次 | 产出 | 审批 | 耗时 |
|------|------|------|------|
| batch-50 | Slice 1-4 | Leader (待定) | — |
