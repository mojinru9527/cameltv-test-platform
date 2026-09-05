import type { ReactNode } from 'react'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { SidebarMenu, SidebarProvider, useSidebar } from '@/components/ui/sidebar'
import { TooltipProvider } from '@/components/ui/tooltip'
import type { MenuItem } from '@/types'
import type { MainNavRow } from '../nav-config'
import { MainNavRows } from '../MainNavRows'
import { NavigationMenuItems } from '../NavigationMenuItems'

/**
 * DEF-20260904-001（Batch 230 部分修复）：侧栏子项此前渲染为无 href 的 `<a>`，
 * 既无 link role 也不可 Tab 聚焦、不能中键/新标签打开。这两处是同一根因的两个实例，
 * 改法不同：MainNavRows 的 onNavigate 是纯导航（必须删 onClick，否则双重导航），
 * NavigationMenuItems 的 goTo 还带移动端收起抽屉的副作用（必须保留该副作用）。
 */

type Navigate = (path: string, label: string) => void

function item(code: string, name: string, path: string): MenuItem {
  return { code, name, path, icon: '', sort: 1 }
}

const GROUP_ROWS: MainNavRow[] = [
  {
    kind: 'group',
    label: '版本验收',
    items: [item('menu:versiontask', '版本验收任务', '/version-tasks')],
  },
]

const BUCKET_ITEMS: MenuItem[] = [
  {
    ...item('menu:system', '系统设置', '/system'),
    children: [item('menu:users', '用户管理', '/system/users')],
  },
]

/** 把 SidebarProvider 内部的移动端抽屉状态暴露出来，否则无法断言 closeMobile。 */
function MobileDrawerProbe() {
  const { openMobile, setOpenMobile } = useSidebar()
  return (
    <>
      <span data-testid="drawer-open">{String(openMobile)}</span>
      <button type="button" onClick={() => setOpenMobile(true)}>打开抽屉</button>
    </>
  )
}

function mockMatchMedia(isMobile: boolean) {
  // useIsMobile 读的是 window.innerWidth，matchMedia 只用于订阅变更
  Object.defineProperty(window, 'innerWidth', {
    writable: true,
    configurable: true,
    value: isMobile ? 500 : 1280,
  })
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    configurable: true,
    value: (query: string) => ({
      matches: isMobile,
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

function renderNav(build: (onNavigate: Navigate) => ReactNode, { mobile = false } = {}) {
  mockMatchMedia(mobile)
  const onNavigate = vi.fn()
  render(
    <MemoryRouter initialEntries={['/workbench']}>
      <TooltipProvider>
        <SidebarProvider defaultOpen>
          <SidebarMenu>{build(onNavigate)}</SidebarMenu>
          <MobileDrawerProbe />
          <Routes>
            <Route path="/workbench" element={<div>工作台</div>} />
            <Route path="/version-tasks" element={<div>版本任务列表页</div>} />
            <Route path="/system/users" element={<div>用户管理页</div>} />
          </Routes>
        </SidebarProvider>
      </TooltipProvider>
    </MemoryRouter>,
  )
  return onNavigate
}

const renderBucket = (mobile = false) =>
  renderNav(
    (onNavigate) => (
      <NavigationMenuItems items={BUCKET_ITEMS} pathname="/workbench" onNavigate={onNavigate} />
    ),
    { mobile },
  )

describe('侧栏子项链接化（DEF-20260904-001）', () => {
  beforeEach(() => window.localStorage.clear())
  afterEach(cleanup)

  it('顶层分组子项渲染为带 href 的真实链接，点击只导航且不回调 onNavigate', () => {
    const onNavigate = renderNav((nav) => (
      <MainNavRows rows={GROUP_ROWS} pathname="/workbench" onNavigate={nav} />
    ))

    const link = screen.getByRole('link', { name: '版本验收任务' })
    expect(link.getAttribute('href')).toBe('/version-tasks')

    fireEvent.click(link)
    expect(screen.getByText('版本任务列表页')).toBeTruthy()
    // 保留 onClick 会与 <Link> 形成双重导航（多压一条历史）
    expect(onNavigate).not.toHaveBeenCalled()
  })

  it('资产与更多分桶子项同样渲染为带 href 的真实链接并可导航', () => {
    renderBucket()

    const link = screen.getByRole('link', { name: '用户管理' })
    expect(link.getAttribute('href')).toBe('/system/users')

    fireEvent.click(link)
    expect(screen.getByText('用户管理页')).toBeTruthy()
  })

  it('移动端点击分桶子项仍会收起抽屉（goTo 的副作用未被误删）', () => {
    renderBucket(true)

    fireEvent.click(screen.getByText('打开抽屉'))
    expect(screen.getByTestId('drawer-open').textContent).toBe('true')

    fireEvent.click(screen.getByRole('link', { name: '用户管理' }))
    expect(screen.getByTestId('drawer-open').textContent).toBe('false')
  })
})
