import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router'
import { beforeEach, describe, expect, it } from 'vitest'

import { useAuthStore } from '@/stores/auth'
import { PasswordChangeBoundary } from '../index'

describe('PasswordChangeBoundary', () => {
  beforeEach(() => {
    useAuthStore.getState().logout()
    useAuthStore.setState({
      user: { id: 61, username: 'forced-user', nickname: 'Forced User', email: '' },
      mustChangePassword: true,
    })
  })

  it('redirects a forced-password user away from a protected route', () => {
    render(
      <MemoryRouter initialEntries={['/testcase']}>
        <Routes>
          <Route
            path="/testcase"
            element={<PasswordChangeBoundary><div>受控页面</div></PasswordChangeBoundary>}
          />
          <Route path="/change-password" element={<div>修改密码</div>} />
        </Routes>
      </MemoryRouter>,
    )

    expect(screen.getByText('修改密码')).toBeTruthy()
    expect(screen.queryByText('受控页面')).toBeNull()
  })

  it('allows protected content after the password requirement is cleared', () => {
    useAuthStore.setState({ mustChangePassword: false })

    render(
      <MemoryRouter initialEntries={['/testcase']}>
        <Routes>
          <Route
            path="/testcase"
            element={<PasswordChangeBoundary><div>受控页面</div></PasswordChangeBoundary>}
          />
          <Route path="/change-password" element={<div>修改密码</div>} />
        </Routes>
      </MemoryRouter>,
    )

    expect(screen.getByText('受控页面')).toBeTruthy()
  })
})
