# 知识中心 tab 拼接修复 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复知识中心切换 tab 时已访问 tab 内容拼接显示的问题（根因：Radix Tabs `forceMount` 模式下 `hidden: !present` 恒为 false，已访问 tab 永不隐藏）。

**Architecture:** 保留 `visitedTabs` 懒挂载+状态保留机制，在 12 个 `TabsContent` 上显式用 Tailwind `hidden` class 按活动状态控制可见性，不再依赖 Radix 的 `hidden` 属性。加交互回归测试防复发。

**Tech Stack:** React 19 / Radix UI Tabs 1.1.x / Vitest + Testing Library / Tailwind CSS

**根因证据（已源码确认）**：`node_modules/@radix-ui/react-tabs/dist/index.mjs` L153-170 —— `present: forceMount || isSelected`，`hidden: !present`；`@radix-ui/react-presence` L23 `children({ present: presence.isPresent })`，forceMount=true 时 `isPresent` 恒 true → `hidden` 恒 false。

---

### Task 1: 写失败测试（KnowledgeTabs 切换后旧 tab 隐藏）

**Files:**
- Create: `test-platform-v2/frontend/src/pages/knowledge/__tests__/KnowledgeTabs.test.tsx`

- [ ] **Step 1: 创建测试文件**

```tsx
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter } from 'react-router'

// 12 个 tab 组件全部 mock 为带 data-testid 的占位，避免真实组件拉 API
vi.mock('@/pages/knowledge/components/OverviewTab', () => ({ default: () => <div data-testid="tab-overview">概览内容</div> }))
vi.mock('@/pages/knowledge/components/ProjectTab', () => ({ default: () => <div data-testid="tab-project">项目知识内容</div> }))
vi.mock('@/pages/knowledge/components/PlatformTab', () => ({ default: () => <div data-testid="tab-platform">平台研发内容</div> }))
vi.mock('@/pages/knowledge/components/SearchTab', () => ({ default: () => <div data-testid="tab-search">检索内容</div> }))
vi.mock('@/pages/knowledge/components/SourceListTab', () => ({ default: () => <div data-testid="tab-sources">知识源内容</div> }))
vi.mock('@/pages/knowledge/components/ArtifactReviewTab', () => ({ default: () => <div data-testid="tab-artifacts">AI 审核台内容</div> }))
vi.mock('@/pages/knowledge/components/GraphTab', () => ({ default: () => <div data-testid="tab-graph">图谱内容</div> }))
vi.mock('@/pages/knowledge/components/EntityTab', () => ({ default: () => <div data-testid="tab-entities">实体内容</div> }))
vi.mock('@/pages/knowledge/components/IterationTab', () => ({ default: () => <div data-testid="tab-iterations">迭代内容</div> }))
vi.mock('@/pages/knowledge/components/WikiTab', () => ({ default: () => <div data-testid="tab-wiki">Wiki 知识库内容</div> }))
vi.mock('@/pages/knowledge/components/WikiDiffTab', () => ({ default: () => <div data-testid="tab-wikidiff">知识差异对比内容</div> }))
vi.mock('@/pages/knowledge/components/SkillsTab', () => ({ default: () => <div data-testid="tab-skills">Skills 内容</div> }))
vi.mock('@/pages/knowledge/components/CaptureDialog', () => ({ default: () => null }))

const { default: KnowledgePage } = await import('@/pages/knowledge')

function renderPage(initialPath = '/knowledge?tab=overview') {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <KnowledgePage />
    </MemoryRouter>,
  )
}

describe('知识中心 tab 切换', () => {
  beforeEach(() => vi.clearAllMocks())

  it('初始只显示概览 tab 内容', () => {
    renderPage()
    expect(screen.getByTestId('tab-overview')).toBeVisible()
    expect(screen.queryByTestId('tab-project')).not.toBeInTheDocument()
  })

  it('切到项目知识后，概览内容隐藏（不拼接）', async () => {
    renderPage()
    fireEvent.click(screen.getByRole('tab', { name: /项目知识/ }))
    await waitFor(() => expect(screen.getByTestId('tab-project')).toBeVisible())
    // 核心断言：已访问过的 overview 仍挂载（状态保留）但不可见
    expect(screen.getByTestId('tab-overview')).not.toBeVisible()
  })

  it('切回概览后，项目知识内容隐藏（状态保留但不可见）', async () => {
    renderPage()
    fireEvent.click(screen.getByRole('tab', { name: /项目知识/ }))
    await waitFor(() => expect(screen.getByTestId('tab-project')).toBeVisible())
    fireEvent.click(screen.getByRole('tab', { name: /概览/ }))
    await waitFor(() => expect(screen.getByTestId('tab-overview')).toBeVisible())
    expect(screen.getByTestId('tab-project')).not.toBeVisible()
  })
})
```

- [ ] **Step 2: 运行测试，确认失败（预期：第二/三个用例失败——overview/project 同时可见）**

Run: `cd test-platform-v2/frontend && npx vitest run src/pages/knowledge/__tests__/KnowledgeTabs.test.tsx`
Expected: 用例 2 失败，断言 `not.toBeVisible()` 不通过（两个 tab 内容都可见，拼接 bug 复现）。

### Task 2: 修复 index.tsx —— 显式 hidden class 控制可见性

**Files:**
- Modify: `test-platform-v2/frontend/src/pages/knowledge/index.tsx`（import 区 + 12 处 TabsContent）

- [ ] **Step 1: 引入 cn 工具**

在现有 import 区（第 1 行 `import { useState } from 'react'` 之后）添加：

```tsx
import { cn } from '@/lib/utils'
```

- [ ] **Step 2: 12 处 TabsContent 加显式 hidden class**

把每个 `<TabsContent value="..." className="mt-4" forceMount={...}>` 改为 `className={cn('mt-4', tab !== '...' && 'hidden')}`。逐处替换（共 12 处，value 分别为 project/platform/overview/search/sources/artifacts/graph/entities/iterations/wiki/wikidiff/skills），例如：

```tsx
<TabsContent value="project" className={cn('mt-4', tab !== 'project' && 'hidden')} forceMount={visitedTabs.has('project') ? true : undefined}>
  <ProjectTab />
</TabsContent>
```

```tsx
<TabsContent value="overview" className={cn('mt-4', tab !== 'overview' && 'hidden')} forceMount={visitedTabs.has('overview') ? true : undefined}>
  <OverviewTab />
</TabsContent>
```

其余 10 处按同一模式替换（value 与 visitedTabs.has 的键保持一致）。

- [ ] **Step 3: 运行测试，确认通过**

Run: `cd test-platform-v2/frontend && npx vitest run src/pages/knowledge/__tests__/KnowledgeTabs.test.tsx`
Expected: 3 个用例全部 PASS（overview 与 project 不再同时可见；状态保留语义不回归——切回后 project 仍挂载）。

### Task 3: 全量自检 + 提交

- [ ] **Step 1: 前端全量门禁**

Run: `cd test-platform-v2/frontend && npm run typecheck`
Expected: 0 错误。

Run: `cd test-platform-v2/frontend && npm run build`
Expected: 构建成功。

Run: `cd test-platform-v2/frontend && npx vitest run`（或受影响子集 + 记录全量基线）
Expected: 无新增失败。

- [ ] **Step 2: 提交**

```bash
git add test-platform-v2/frontend/src/pages/knowledge/index.tsx test-platform-v2/frontend/src/pages/knowledge/__tests__/KnowledgeTabs.test.tsx
git commit -m "fix(batch): 知识中心 tab 切换拼接 — forceMount 下 Radix hidden 失效，改显式 hidden class 控制可见性"
```

### Task 4: 手动验证（本地浏览器）

- [ ] **Step 1: 起本地前后端**（按 test-platform-v2/CLAUDE.md：后端 `uvicorn app.main:app --reload --port 8000`，前端 `npm run dev`，端口 5173）
- [ ] **Step 2: 登录进入知识中心，依次点击 概览 → 项目知识 → 概览**
  Expected: 任意时刻只显示当前 tab 内容，无拼接；切回概览后项目知识 tab 的状态（如已加载数据）不重置。
- [ ] **Step 3: 确认 test 环境部署**：若 test 环境仍拼接，确认其构建版本 ≥ 本修复合入后的部署（旧构建需随下次部署刷新）。

---

**Self-review 记录**：spec §6（C 子项目）覆盖——复现确认（根因已在源码层确认，本计划 Task 4 Step 3 补充环境确认）、修复（Task 2）、交互回归测试防复发（Task 1）。无占位符。测试中 `getByRole('tab', { name: /项目知识/ })` 依赖 TabsTrigger 文本（含图标 aria 忽略，Radix 按钮 name 来自文本内容，匹配现有页面文案）。
