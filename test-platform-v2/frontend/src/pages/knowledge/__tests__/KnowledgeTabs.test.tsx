import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter } from 'react-router'

// 仓库未安装 @testing-library/jest-dom，这里用 expect.extend 提供语义对齐的最小实现。
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

// (batch-212) 权限 stub：普通用户（false）只读 3 Tab；维护者（true）可见全部。
const authStub = vi.hoisted(() => ({ hasPerm: () => false }))
vi.mock('@/stores/auth', () => ({
  useAuthStore: (selector: (state: { hasPerm: (code: string) => boolean }) => unknown) =>
    selector({ hasPerm: (code: string) => authStub.hasPerm(code) }),
}))

const { default: KnowledgePage } = await import('@/pages/knowledge')

function renderPage(initialPath = '/knowledge') {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <KnowledgePage />
    </MemoryRouter>,
  )
}

// Radix Tabs 1.1.x 的 tab 切换在 onMouseDown 触发
function clickTab(name: string | RegExp) {
  const tab = screen.getByRole('tab', { name })
  fireEvent.mouseDown(tab, { button: 0 })
  fireEvent.click(tab)
}

describe('知识中心 tab 收敛（batch-212）', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    authStub.hasPerm = () => false
  })

  it('普通用户只读 3 Tab：项目知识/平台研发/检索，默认项目知识', () => {
    renderPage()
    expect(screen.getByTestId('tab-project')).toBeVisible()
    expect(screen.getByRole('tab', { name: /项目知识/ })).toBeTruthy()
    expect(screen.getByRole('tab', { name: /平台研发/ })).toBeTruthy()
    expect(screen.getByRole('tab', { name: /检索/ })).toBeTruthy()
    // 专家/维护 Tab 不再出现
    expect(screen.queryByRole('tab', { name: /概览/ })).toBeNull()
    expect(screen.queryByRole('tab', { name: /AI 审核台/ })).toBeNull()
    expect(screen.queryByRole('tab', { name: /图谱/ })).toBeNull()
    expect(screen.queryByRole('tab', { name: /知识源/ })).toBeNull()
    expect(screen.queryByTestId('tab-overview')).not.toBeInTheDocument()
  })

  it('普通用户深链到维护 Tab（?tab=graph）自动回落项目知识，不 404', () => {
    renderPage('/knowledge?tab=graph')
    expect(screen.getByTestId('tab-project')).toBeVisible()
    expect(screen.queryByTestId('tab-graph')).not.toBeInTheDocument()
  })

  it('普通用户切到检索 Tab 正常显示', async () => {
    renderPage()
    clickTab(/检索/)
    await waitFor(() => expect(screen.getByTestId('tab-search')).toBeVisible())
    expect(screen.getByTestId('tab-project')).not.toBeVisible()
  })

  it('维护者/管理员可见全部 Tab，默认概览', () => {
    authStub.hasPerm = () => true
    renderPage()
    expect(screen.getByTestId('tab-overview')).toBeVisible()
    for (const name of [/项目知识/, /平台研发/, /检索/, /AI 审核台/, /图谱/, /知识源/, /实体/, /迭代/, /Wiki 知识库/, /知识差异对比/, /Skills/]) {
      expect(screen.getByRole('tab', { name })).toBeTruthy()
    }
  })

  it('维护者切到项目知识后概览隐藏（状态保留但不可见）', async () => {
    authStub.hasPerm = () => true
    renderPage()
    clickTab(/项目知识/)
    await waitFor(() => expect(screen.getByTestId('tab-project')).toBeVisible())
    expect(screen.getByTestId('tab-overview')).not.toBeVisible()
  })
})