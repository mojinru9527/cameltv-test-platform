import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'

vi.mock('@/hooks/useDocumentTitle', () => ({ useDocumentTitle: vi.fn() }))
vi.mock('@/api/auth', () => ({ login: vi.fn() }))

import LoginPage from '../index'

describe('登录页敏感信息保护', () => {
  it('不预填账号密码，也不公开可复用的默认凭据', () => {
    const { container } = render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>,
    )

    const heading = screen.getByRole('heading', { name: 'CamelTv 测试平台' })
    expect(heading).toBeTruthy()
    expect((screen.getByLabelText('用户名') as HTMLInputElement).value).toBe('')
    expect((screen.getByLabelText('密码') as HTMLInputElement).value).toBe('')
    expect(screen.queryByText(/默认账号/i)).toBeNull()
    expect(screen.queryByText(/admin\d{3,}/i)).toBeNull()

    const pageShell = container.firstElementChild
    const card = heading.closest('[data-slot="card"]')
    expect(pageShell?.classList.contains('min-h-[100dvh]')).toBe(true)
    expect(pageShell?.classList.contains('bg-background')).toBe(true)
    expect(pageShell?.classList.contains('px-4')).toBe(true)
    expect(pageShell?.classList.contains('h-screen')).toBe(false)
    expect(pageShell?.classList.contains('bg-gradient-to-br')).toBe(false)
    expect(card?.classList.contains('w-full')).toBe(true)
    expect(card?.classList.contains('max-w-[380px]')).toBe(true)
    expect(card?.classList.contains('w-[380px]')).toBe(false)
    expect(card?.classList.contains('shadow-2xl')).toBe(false)
  })
})
