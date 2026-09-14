import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'

const mockFetchPublicAccess = vi.fn()
const mockForgotPassword = vi.fn()

vi.mock('@/hooks/useDocumentTitle', () => ({ useDocumentTitle: vi.fn() }))
vi.mock('@/api/auth', () => ({
  fetchPublicAccess: (...args: unknown[]) => mockFetchPublicAccess(...args),
  forgotPassword: (...args: unknown[]) => mockForgotPassword(...args),
}))

import ForgotPasswordPage from '../index'

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
})

describe('ForgotPasswordPage', () => {
  it('does not claim mail was sent when SMTP is not configured', async () => {
    mockFetchPublicAccess.mockResolvedValue({
      registration_enabled: true,
      invite_code_required: false,
      password_reset_email_enabled: false,
      modules: [],
    })
    mockForgotPassword.mockResolvedValue(null)

    render(
      <MemoryRouter>
        <ForgotPasswordPage />
      </MemoryRouter>,
    )

    expect(await screen.findByText(/当前部署未配置完整邮件发送链路/)).toBeTruthy()
    fireEvent.change(screen.getByLabelText('用户名'), { target: { value: 'alice' } })
    fireEvent.click(screen.getByRole('button', { name: '发送重置链接' }))

    await waitFor(() => expect(mockForgotPassword).toHaveBeenCalledWith('alice'))
    expect(await screen.findByText(/本次请求不会自动发送邮件/)).toBeTruthy()
  })

  it('keeps a generic response when email delivery is available', async () => {
    mockFetchPublicAccess.mockResolvedValue({
      registration_enabled: true,
      invite_code_required: false,
      password_reset_email_enabled: true,
      modules: [],
    })
    mockForgotPassword.mockResolvedValue(null)

    render(
      <MemoryRouter>
        <ForgotPasswordPage />
      </MemoryRouter>,
    )

    fireEvent.change(screen.getByLabelText('用户名'), { target: { value: 'missing-user' } })
    fireEvent.click(screen.getByRole('button', { name: '发送重置链接' }))

    expect(await screen.findByText(/请检查收件箱和垃圾邮件目录/)).toBeTruthy()
    expect(screen.getByText(/不会显示账号是否存在/)).toBeTruthy()
  })
})
