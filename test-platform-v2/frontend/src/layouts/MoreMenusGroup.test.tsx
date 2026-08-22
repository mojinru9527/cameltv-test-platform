import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { SidebarProvider } from '@/components/ui/sidebar'
import { TooltipProvider } from '@/components/ui/tooltip'
import type { MenuItem } from '@/types'
import { MoreMenusGroup } from './MoreMenusGroup'
import { MORE_MENUS_STORAGE_KEY } from './nav-config'

const MORE_ITEMS: MenuItem[] = [
  { code: 'menu:report', name: '报告中心', path: '/report', icon: 'BarChartOutlined', sort: 13 },
  { code: 'menu:defect', name: '缺陷管理', path: '/defect', icon: 'BugOutlined', sort: 16 },
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
        <MoreMenusGroup items={MORE_ITEMS} pathname={pathname} onNavigate={onNavigate} />
      </SidebarProvider>
    </TooltipProvider>,
  )
  return { onNavigate }
}

describe('MoreMenusGroup（c165-3 更多功能折叠组）', () => {
  beforeEach(() => {
    window.localStorage.clear()
    mockMatchMedia()
  })
  afterEach(cleanup)

  it('默认收起：低频项不渲染，组头显示名称与数量', () => {
    renderGroup()
    expect(screen.getByText('更多功能')).toBeTruthy()
    expect(screen.getByText('2')).toBeTruthy()
    expect(screen.queryByText('报告中心')).toBeNull()
    expect(screen.queryByText('缺陷管理')).toBeNull()
  })

  it('点击组头展开并渲染低频项，状态写入 localStorage；再次点击收起', () => {
    renderGroup()
    fireEvent.click(screen.getByText('更多功能'))
    expect(screen.getByText('报告中心')).toBeTruthy()
    expect(screen.getByText('缺陷管理')).toBeTruthy()
    expect(window.localStorage.getItem(MORE_MENUS_STORAGE_KEY)).toBe('1')

    fireEvent.click(screen.getByText('更多功能'))
    expect(window.localStorage.getItem(MORE_MENUS_STORAGE_KEY)).toBe('0')
  })

  it('localStorage 已记忆展开时初始即展开', () => {
    window.localStorage.setItem(MORE_MENUS_STORAGE_KEY, '1')
    renderGroup()
    expect(screen.getByText('报告中心')).toBeTruthy()
  })

  it('当前路径命中组内菜单时自动展开（不写持久化状态）', () => {
    renderGroup('/report')
    expect(screen.getByText('报告中心')).toBeTruthy()
    expect(window.localStorage.getItem(MORE_MENUS_STORAGE_KEY)).toBeNull()
  })

  it('items 为空时不渲染任何内容', () => {
    const { container } = render(
      <TooltipProvider>
        <SidebarProvider defaultOpen>
          <MoreMenusGroup items={[]} pathname="/workbench" onNavigate={vi.fn()} />
        </SidebarProvider>
      </TooltipProvider>,
    )
    expect(container.textContent).toBe('')
  })

  it('侧边栏图标折叠模式下：不做折叠组，低频项直接平铺', () => {
    renderGroup('/workbench', false)
    expect(screen.queryByText('更多功能')).toBeNull()
    expect(screen.getByText('报告中心')).toBeTruthy()
    expect(screen.getByText('缺陷管理')).toBeTruthy()
  })
})
