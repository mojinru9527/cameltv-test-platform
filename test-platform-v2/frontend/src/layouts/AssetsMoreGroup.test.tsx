import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { SidebarProvider } from '@/components/ui/sidebar'
import { TooltipProvider } from '@/components/ui/tooltip'
import type { AssetSection } from './nav-config'
import { ASSETS_MORE_STORAGE_KEY } from './nav-config'
import { AssetsMoreGroup } from './AssetsMoreGroup'

const SECTIONS: AssetSection[] = [
  {
    label: '资产',
    items: [
      { code: 'menu:testcase', name: '用例服务', path: '/testcase', icon: 'ProfileOutlined', sort: 7 },
      { code: 'menu:apitest', name: '接口测试', path: '/apitest', icon: 'ApiOutlined', sort: 9 },
    ],
  },
  {
    label: '专家',
    items: [
      { code: 'menu:runtime', name: 'Durable Runtime', path: '/admin/workers', icon: '', sort: 25 },
    ],
  },
]

function mockMatchMedia() {
  // jsdom 无 matchMedia：SidebarProvider 的 useIsMobile 依赖它
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: (query: string) => ({
      matches: false,
      media: query,
      onchange: null,
      addListener: () => {},
      removeListener: () => {},
      addEventListener: () => {},
      removeEventListener: () => {},
      dispatchEvent: () => false,
    }),
  })
}

function renderGroup(pathname = '/workbench', sidebarOpen = true) {
  const onNavigate = vi.fn()
  render(
    <TooltipProvider>
      <SidebarProvider defaultOpen={sidebarOpen}>
        <AssetsMoreGroup sections={SECTIONS} pathname={pathname} onNavigate={onNavigate} />
      </SidebarProvider>
    </TooltipProvider>,
  )
  return { onNavigate }
}

describe('AssetsMoreGroup（batch-212 资产与更多折叠容器）', () => {
  beforeEach(() => {
    window.localStorage.clear()
    mockMatchMedia()
  })
  afterEach(cleanup)

  it('默认收起：分桶项不渲染，组头显示名称与数量（只计条目数）', () => {
    renderGroup()
    expect(screen.getByText('资产与更多')).toBeTruthy()
    expect(screen.getByText('3')).toBeTruthy()
    expect(screen.queryByText('用例服务')).toBeNull()
    expect(screen.queryByText('Durable Runtime')).toBeNull()
  })

  it('点击组头展开并渲染分桶头与分桶项，状态写入 localStorage；再次点击收起', () => {
    renderGroup()
    fireEvent.click(screen.getByText('资产与更多'))
    expect(screen.getByText('资产')).toBeTruthy()
    expect(screen.getByText('专家')).toBeTruthy()
    expect(screen.getByText('用例服务')).toBeTruthy()
    expect(screen.getByText('Durable Runtime')).toBeTruthy()
    expect(window.localStorage.getItem(ASSETS_MORE_STORAGE_KEY)).toBe('1')

    fireEvent.click(screen.getByText('资产与更多'))
    expect(window.localStorage.getItem(ASSETS_MORE_STORAGE_KEY)).toBe('0')
  })

  it('localStorage 已记忆展开时初始即展开', () => {
    window.localStorage.setItem(ASSETS_MORE_STORAGE_KEY, '1')
    renderGroup()
    expect(screen.getByText('用例服务')).toBeTruthy()
  })

  it('当前路径命中分桶项时自动展开（不写持久化状态）', () => {
    renderGroup('/testcase')
    expect(screen.getByText('用例服务')).toBeTruthy()
    expect(window.localStorage.getItem(ASSETS_MORE_STORAGE_KEY)).toBeNull()
  })

  it('sections 为空时不渲染任何内容', () => {
    const { container } = render(
      <TooltipProvider>
        <SidebarProvider defaultOpen>
          <AssetsMoreGroup sections={[]} pathname="/workbench" onNavigate={vi.fn()} />
        </SidebarProvider>
      </TooltipProvider>,
    )
    expect(container.textContent).toBe('')
  })

  it('侧边栏图标折叠模式下：不做折叠组，分桶项直接平铺', () => {
    renderGroup('/workbench', false)
    expect(screen.queryByText('资产与更多')).toBeNull()
    expect(screen.getByText('用例服务')).toBeTruthy()
    expect(screen.getByText('Durable Runtime')).toBeTruthy()
  })
})