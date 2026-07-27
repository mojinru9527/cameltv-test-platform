import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'

vi.mock('@/hooks/useDocumentTitle', () => ({ useDocumentTitle: vi.fn() }))
vi.mock('@/api/auth', () => ({ login: vi.fn() }))

import LoginPage from '../index'

describe('登录页敏感信息保护', () => {
  it('不预填账号密码，也不公开可复用的默认凭据', () => {
    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>,
    )

    expect((screen.getByLabelText('用户名') as HTMLInputElement).value).toBe('')
    expect((screen.getByLabelText('密码') as HTMLInputElement).value).toBe('')
    expect(screen.queryByText(/默认账号/i)).toBeNull()
    expect(screen.queryByText(/admin\d{3,}/i)).toBeNull()
  })
})
