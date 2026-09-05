import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { createMemoryRouter, Outlet, RouterProvider } from 'react-router'

vi.mock('@/config/aitde', () => ({ useAitdeV3Enabled: () => true }))

const { LegacyNoticeBanner } = await import('@/components/legacy/LegacyNoticeBanner')

const BANNER_LABEL = 'V4.0 旧版入口收敛提示'

/**
 * 复刻真实路由表的形状：splat 叶子是布局路由的**子**路由（router/index.tsx:507），
 * 因此 useMatches() 的最后一项才是 404 叶子。单测能锁住这段判定逻辑，
 * 但真实路由表的越界前缀仍须按 Design §6 条件 6 在浏览器实测四条路径。
 */
function renderAt(path: string) {
  const router = createMemoryRouter(
    [
      {
        path: '/',
        element: (
          <>
            <LegacyNoticeBanner />
            <Outlet />
          </>
        ),
        children: [
          { path: 'defect', element: <div>缺陷列表</div> },
          { path: 'knowledge', element: <div>知识中心</div> },
          { path: 'missions', element: <div>Mission 工作台</div> },
          { path: '*', element: <div>页面不存在</div> },
        ],
      },
    ],
    { initialEntries: [path] },
  )
  render(<RouterProvider router={router} />)
}

describe('LegacyNoticeBanner 404 边界（DEF-20260905-009）', () => {
  it.each(['/defect', '/knowledge'])('真实历史入口 %s 显示横幅', (path) => {
    renderAt(path)
    expect(screen.getByRole('status', { name: BANNER_LABEL })).toBeTruthy()
  })

  it('/defects 落到 404 时不显示横幅（前缀越界）', () => {
    renderAt('/defects')
    expect(screen.getByText('页面不存在')).toBeTruthy()
    expect(screen.queryByRole('status', { name: BANNER_LABEL })).toBeNull()
  })

  it('/nonexistent 落到 404 时不显示横幅', () => {
    renderAt('/nonexistent')
    expect(screen.getByText('页面不存在')).toBeTruthy()
    expect(screen.queryByRole('status', { name: BANNER_LABEL })).toBeNull()
  })

  it('非历史前缀的真实路由不显示横幅（前缀判定未被削弱）', () => {
    renderAt('/missions')
    expect(screen.getByText('Mission 工作台')).toBeTruthy()
    expect(screen.queryByRole('status', { name: BANNER_LABEL })).toBeNull()
  })
})
