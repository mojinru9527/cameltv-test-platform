import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router'
import { beforeEach, describe, expect, it } from 'vitest'

import { useAuthStore } from '@/stores/auth'
import { RequirePermission } from '../guard'

function renderGuarded() {
  return render(
    <MemoryRouter initialEntries={['/runs']}>
      <Routes>
        <Route
          path="/runs"
          element={
            <RequirePermission code="menu:aiqe_runs">
              <div>执行中心内容</div>
            </RequirePermission>
          }
        />
        <Route path="/login" element={<div>登录页</div>} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('RequirePermission（batch-336：执行中心路由守卫）', () => {
  beforeEach(() => {
    useAuthStore.getState().logout()
  })

  it('缺少 menu:aiqe_runs → 渲染 403，不渲染页面', () => {
    useAuthStore.setState({
      user: { id: 1, username: 'tester', nickname: 'T', email: '' },
      permissions: ['menu:defect'],
    })

    renderGuarded()

    expect(screen.getByTestId('forbidden-page')).toBeTruthy()
    expect(screen.queryByText('执行中心内容')).toBeNull()
  })

  it('拥有 menu:aiqe_runs → 渲染页面', () => {
    useAuthStore.setState({
      user: { id: 1, username: 'tester', nickname: 'T', email: '' },
      permissions: ['menu:defect', 'menu:aiqe_runs'],
    })

    renderGuarded()

    expect(screen.getByText('执行中心内容')).toBeTruthy()
    expect(screen.queryByTestId('forbidden-page')).toBeNull()
  })

  it('超级权限 * → 放行', () => {
    useAuthStore.setState({
      user: { id: 1, username: 'admin', nickname: 'A', email: '' },
      permissions: ['*'],
    })

    renderGuarded()

    expect(screen.getByText('执行中心内容')).toBeTruthy()
  })

  it('未登录 → 跳转登录页', () => {
    renderGuarded()

    expect(screen.getByText('登录页')).toBeTruthy()
    expect(screen.queryByText('执行中心内容')).toBeNull()
  })
})
