import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'

const mockResetPassword = vi.fn()
const mockNavigate = vi.fn()
const mockToastSuccess = vi.fn()

vi.mock('@/hooks/useDocumentTitle', () => ({ useDocumentTitle: vi.fn() }))
vi.mock('@/api/auth', () => ({
  resetPassword: (...args: unknown[]) => mockResetPassword(...args),
}))
vi.mock('sonner', () => ({ toast: { success: (...args: unknown[]) => mockToastSuccess(...args) } }))
vi.mock('react-router', async (importOriginal) => {
  const actual = await importOriginal<typeof import('react-router')>()
  return { ...actual, useNavigate: () => mockNavigate }
})

import ResetPasswordPage from '../index'

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
})

describe('ResetPasswordPage', () => {
  it('shows a recoverable state when the token is missing', () => {
    render(
      <MemoryRouter initialEntries={['/reset-password']}>
        <ResetPasswordPage />
      </MemoryRouter>,
    )

    expect(screen.getByRole('heading', { name: '链接无效' })).toBeTruthy()
    expect(screen.getByRole('link', { name: '重新申请' }).getAttribute('href')).toBe('/forgot-password')
  })

  it('submits the token and returns to login after reset', async () => {
    mockResetPassword.mockResolvedValue(null)
    render(
      <MemoryRouter initialEntries={['/reset-password?token=reset-token']}>
        <ResetPasswordPage />
      </MemoryRouter>,
    )

    fireEvent.change(screen.getByLabelText('新密码'), { target: { value: 'new-password-123' } })
    fireEvent.change(screen.getByLabelText('确认新密码'), { target: { value: 'new-password-123' } })
    fireEvent.click(screen.getByRole('button', { name: '重置密码' }))

    await waitFor(() => expect(mockResetPassword).toHaveBeenCalledWith('reset-token', 'new-password-123'))
    expect(mockToastSuccess).toHaveBeenCalledWith('密码已重置，请使用新密码登录')
    expect(mockNavigate).toHaveBeenCalledWith('/login', { replace: true })
  })
})
