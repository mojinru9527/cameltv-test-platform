import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'

const mockLogin = vi.fn()
const mockSetLogin = vi.fn()

vi.mock('@/api/auth', () => ({ login: (...args: unknown[]) => mockLogin(...args) }))
vi.mock('@/stores/auth', () => ({
  useAuthStore: (selector: (state: { setLogin: typeof mockSetLogin }) => unknown) => selector({ setLogin: mockSetLogin }),
}))
vi.mock('sonner', () => ({ toast: { success: vi.fn(), error: vi.fn() } }))

import LoginForm from '../LoginForm'

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
})

describe('LoginForm password assistance', () => {
  it('links to recovery and toggles password visibility without submitting', () => {
    render(
      <MemoryRouter>
        <LoginForm onSuccess={vi.fn()} />
      </MemoryRouter>,
    )

    const password = screen.getByLabelText('密码') as HTMLInputElement
    expect(password.type).toBe('password')
    expect(screen.getByRole('link', { name: '忘记密码？' }).getAttribute('href')).toBe('/forgot-password')

    fireEvent.click(screen.getByRole('button', { name: '显示密码' }))
    expect(password.type).toBe('text')
    expect(screen.getByRole('button', { name: '隐藏密码' }).getAttribute('aria-pressed')).toBe('true')
    expect(mockLogin).not.toHaveBeenCalled()
  })

  it('shows a non-blocking Caps Lock hint', () => {
    render(
      <MemoryRouter>
        <LoginForm onSuccess={vi.fn()} />
      </MemoryRouter>,
    )

    const password = screen.getByLabelText('密码')
    const event = new KeyboardEvent('keydown', { key: 'A', bubbles: true })
    Object.defineProperty(event, 'getModifierState', {
      value: (key: string) => key === 'CapsLock',
    })
    fireEvent(password, event)

    expect(screen.getByRole('status').textContent).toContain('Caps Lock 已开启')
  })
})
