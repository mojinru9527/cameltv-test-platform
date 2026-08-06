import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'

const mockGet = vi.fn()
const mockSetProjects = vi.fn()
const mockSetCurrentProject = vi.fn()
const mockHasPerm = vi.fn()

vi.mock('@/hooks/useDocumentTitle', () => ({ useDocumentTitle: vi.fn() }))
vi.mock('@/api/client', () => ({
  default: {
    get: (...args: unknown[]) => mockGet(...args),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}))
vi.mock('@/api/system', () => ({
  fetchUsers: vi.fn().mockResolvedValue([]),
  fetchRoles: vi.fn().mockResolvedValue([]),
}))
vi.mock('@/stores/auth', () => ({
  useAuthStore: () => ({
    user: { id: 1, username: 'alice', nickname: 'Alice', email: '' },
    setProjects: mockSetProjects,
    setCurrentProject: mockSetCurrentProject,
    hasPerm: mockHasPerm,
  }),
}))
vi.mock('react-router', async (importOriginal) => {
  const actual = await importOriginal<typeof import('react-router')>()
  return { ...actual, useNavigate: () => vi.fn() }
})

import MyProjectsPage from '../index'

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
})

describe('我的项目页', () => {
  it('展示我的项目列表与负责人徽标', async () => {
    mockHasPerm.mockReturnValue(true)
    mockGet.mockImplementation((url: string) => {
      if (url === '/projects') {
        return Promise.resolve([
          { id: 1, code: 'MYAPP', name: '我的应用', description: '', status: 1, owner_id: 1 },
        ])
      }
      return Promise.resolve([])
    })
    render(
      <MemoryRouter>
        <MyProjectsPage />
      </MemoryRouter>,
    )
    expect(await screen.findByText('我的应用')).toBeTruthy()
    expect(screen.getByText('负责人')).toBeTruthy()
    expect(screen.getByRole('button', { name: /新建项目/ })).toBeTruthy()
  })

  it('无项目时展示空态与新建入口', async () => {
    mockHasPerm.mockReturnValue(true)
    mockGet.mockResolvedValue([])
    render(
      <MemoryRouter>
        <MyProjectsPage />
      </MemoryRouter>,
    )
    expect(await screen.findByText('暂无项目')).toBeTruthy()
    expect(screen.getByText(/创建你的第一个项目/)).toBeTruthy()
  })

  it('无自助创建权限时不显示新建按钮', async () => {
    mockHasPerm.mockReturnValue(false)
    mockGet.mockResolvedValue([])
    render(
      <MemoryRouter>
        <MyProjectsPage />
      </MemoryRouter>,
    )
    await waitFor(() => expect(mockGet).toHaveBeenCalled())
    expect(screen.queryByRole('button', { name: /新建项目/ })).toBeNull()
  })
})
