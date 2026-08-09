import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const mockRegister = vi.fn()
const mockFetchPublicAccess = vi.fn()
const mockNavigate = vi.fn()
const mockSetLogin = vi.fn()

vi.mock('@/hooks/useDocumentTitle', () => ({ useDocumentTitle: vi.fn() }))
vi.mock('@/api/auth', () => ({
  fetchPublicAccess: (...args: unknown[]) => mockFetchPublicAccess(...args),
  register: (...args: unknown[]) => mockRegister(...args),
}))
vi.mock('@/stores/auth', () => ({
  useAuthStore: (selector: any) => selector({ setLogin: mockSetLogin }),
}))
vi.mock('react-router', async (importOriginal) => {
  const actual = await importOriginal<typeof import('react-router')>()
  return { ...actual, useNavigate: () => mockNavigate }
})

import RegisterPage from '../index'

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
})

beforeEach(() => {
  mockFetchPublicAccess.mockResolvedValue({
    registration_enabled: true,
    invite_code_required: false,
    modules: [],
  })
})

function fillForm(overrides: Partial<Record<string, string>> = {}) {
  const values: Record<string, string> = {
    用户名: 'alice',
    密码: 'secret123',
    确认密码: 'secret123',
    ...overrides,
  }
  for (const [label, value] of Object.entries(values)) {
    fireEvent.change(screen.getByLabelText(label), { target: { value } })
  }
}

describe('注册页', () => {
  it('默认提供无需邀请码的普通注册入口', async () => {
    render(
      <MemoryRouter>
        <RegisterPage />
      </MemoryRouter>,
    )
    expect(screen.getByRole('heading', { name: '注册 CamelTv 测试平台' })).toBeTruthy()
    expect(screen.getByLabelText('用户名')).toBeTruthy()
    expect(screen.getByLabelText('密码')).toBeTruthy()
    expect(screen.getByLabelText('确认密码')).toBeTruthy()
    expect(await screen.findByLabelText('平台邀请码（可选）')).toBeTruthy()
    expect(screen.getByText('无需邀请码即可创建账号')).toBeTruthy()
    expect(screen.getByText('去登录')).toBeTruthy()
  })

  it('密码过短时展示校验错误', async () => {
    render(
      <MemoryRouter>
        <RegisterPage />
      </MemoryRouter>,
    )
    fillForm({ 密码: '123', 确认密码: '123' })
    fireEvent.click(screen.getByRole('button', { name: '注册并登录' }))
    expect(await screen.findByText('密码至少 6 位')).toBeTruthy()
    expect(mockRegister).not.toHaveBeenCalled()
  })

  it('两次密码不一致时展示错误', async () => {
    render(
      <MemoryRouter>
        <RegisterPage />
      </MemoryRouter>,
    )
    fillForm({ 密码: 'secret123', 确认密码: 'different1' })
    fireEvent.click(screen.getByRole('button', { name: '注册并登录' }))
    expect(await screen.findByText('两次输入的密码不一致')).toBeTruthy()
    expect(mockRegister).not.toHaveBeenCalled()
  })

  it('提交成功后写入登录态并跳转我的项目', async () => {
    mockRegister.mockResolvedValue({
      access_token: 'tok',
      user: { id: 9, username: 'alice', nickname: 'Alice', email: '' },
      projects: [],
      permissions: ['project:self_create'],
    })
    render(
      <MemoryRouter>
        <RegisterPage />
      </MemoryRouter>,
    )
    fillForm()
    fireEvent.click(screen.getByRole('button', { name: '注册并登录' }))
    await waitFor(() => expect(mockRegister).toHaveBeenCalledTimes(1))
    expect(mockRegister).toHaveBeenCalledWith({
      username: 'alice',
      nickname: '',
      email: '',
      password: 'secret123',
      invite_code: '',
      project_invite_token: '',
    })
    expect(mockSetLogin).toHaveBeenCalledTimes(1)
    expect(mockNavigate).toHaveBeenCalledWith('/my-projects', { replace: true })
  })

  it('受控环境启用平台邀请码时改为必填', async () => {
    mockFetchPublicAccess.mockResolvedValue({
      registration_enabled: true,
      invite_code_required: true,
      modules: [],
    })
    render(
      <MemoryRouter>
        <RegisterPage />
      </MemoryRouter>,
    )
    expect(await screen.findByLabelText('平台邀请码')).toBeTruthy()
    fillForm()
    fireEvent.click(screen.getByRole('button', { name: '注册并登录' }))
    expect(await screen.findByText('请输入平台邀请码')).toBeTruthy()
    expect(mockRegister).not.toHaveBeenCalled()
  })

  it('携带项目邀请参数时展示提示并随请求提交', async () => {
    mockRegister.mockResolvedValue({
      access_token: 'tok',
      user: { id: 10, username: 'alice', nickname: 'Alice', email: '' },
      projects: [],
      permissions: [],
    })
    render(
      <MemoryRouter initialEntries={['/register?invite=TOKEN123']}>
        <RegisterPage />
      </MemoryRouter>,
    )
    expect(screen.getByText(/你正被邀请加入一个项目/)).toBeTruthy()
    fillForm()
    fireEvent.click(screen.getByRole('button', { name: '注册并登录' }))
    await waitFor(() => expect(mockRegister).toHaveBeenCalledTimes(1))
    expect(mockRegister).toHaveBeenCalledWith(
      expect.objectContaining({ project_invite_token: 'TOKEN123' }),
    )
  })
})
