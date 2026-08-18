import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter } from 'react-router'

// 仓库未安装 @testing-library/jest-dom（package.json 无此依赖，现有测试也不使用其 matcher），
// 这里用 expect.extend 提供语义对齐的最小实现，jsdom 无样式表，可见性按
// Radix hidden 属性 + Tailwind hidden class（修复方案的控制机制）沿祖先链判定。
expect.extend({
  toBeVisible(received: Element) {
    let node: Element | null = received
    while (node) {
      if (node.hasAttribute('hidden')) {
        return { pass: false, message: () => 'element (or an ancestor) is hidden via the hidden attribute' }
      }
      if (node.classList.contains('hidden')) {
        return { pass: false, message: () => 'element (or an ancestor) is hidden via the Tailwind hidden class' }
      }
      const style = (node as HTMLElement).style
      if (style && (style.display === 'none' || style.visibility === 'hidden')) {
        return { pass: false, message: () => 'element (or an ancestor) is hidden via inline style' }
      }
      node = node.parentElement
    }
    return { pass: true, message: () => 'element is visible' }
  },
  toBeInTheDocument(received: Element | null) {
    const pass = received !== null && document.documentElement.contains(received)
    return { pass, message: () => (pass ? 'element is in the document' : 'element is not in the document') }
  },
})

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

// Radix Tabs 1.1.x 的 tab 切换在 onMouseDown 触发（fireEvent.click 无效），
// 与仓库既有范式一致（见 requirement/__tests__/AiResultModal.test.tsx）
function clickTab(name: string | RegExp) {
  const tab = screen.getByRole('tab', { name })
  fireEvent.mouseDown(tab, { button: 0 })
  fireEvent.click(tab)
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
    clickTab(/项目知识/)
    await waitFor(() => expect(screen.getByTestId('tab-project')).toBeVisible())
    expect(screen.getByTestId('tab-overview')).not.toBeVisible()
  })

  it('切回概览后，项目知识内容隐藏（状态保留但不可见）', async () => {
    renderPage()
    clickTab(/项目知识/)
    await waitFor(() => expect(screen.getByTestId('tab-project')).toBeVisible())
    clickTab(/概览/)
    await waitFor(() => expect(screen.getByTestId('tab-overview')).toBeVisible())
    expect(screen.getByTestId('tab-project')).not.toBeVisible()
  })
})
