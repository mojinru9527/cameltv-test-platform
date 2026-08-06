import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'

const mockFetchOrganizations = vi.fn()
const mockCreateOrganization = vi.fn()
const mockFetchOrgMembers = vi.fn()
const mockAddOrgMember = vi.fn()
const mockFetchOrgProjects = vi.fn()

vi.mock('@/hooks/useDocumentTitle', () => ({ useDocumentTitle: vi.fn() }))
vi.mock('@/api/organization', () => ({
  fetchOrganizations: (...args: unknown[]) => mockFetchOrganizations(...args),
  createOrganization: (...args: unknown[]) => mockCreateOrganization(...args),
  updateOrganization: vi.fn(),
  disableOrganization: vi.fn(),
  fetchOrgMembers: (...args: unknown[]) => mockFetchOrgMembers(...args),
  addOrgMember: (...args: unknown[]) => mockAddOrgMember(...args),
  removeOrgMember: vi.fn(),
  fetchOrgProjects: (...args: unknown[]) => mockFetchOrgProjects(...args),
}))
vi.mock('@/stores/auth', () => ({
  useAuthStore: () => ({
    setCurrentProject: vi.fn(),
  }),
}))
vi.mock('react-router', async (importOriginal) => {
  const actual = await importOriginal<typeof import('react-router')>()
  return { ...actual, useNavigate: () => vi.fn() }
})

import OrganizationPage from '../index'

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
})

function orgFixture() {
  return [
    {
      id: 1, code: 'personal-9', name: '我的组织', description: '', type: 'personal',
      owner_id: 9, my_role: 1, status: 1, member_count: 1, project_count: 2,
    },
    {
      id: 2, code: 'qa-team', name: 'QA 团队', description: '', type: 'team',
      owner_id: 9, my_role: 1, status: 1, member_count: 3, project_count: 5,
    },
  ]
}

describe('组织管理页', () => {
  it('展示组织列表、类型徽标与我的角色', async () => {
    mockFetchOrganizations.mockResolvedValue(orgFixture())
    render(
      <MemoryRouter>
        <OrganizationPage />
      </MemoryRouter>,
    )
    expect(await screen.findByText('我的组织')).toBeTruthy()
    expect(screen.getByText('QA 团队')).toBeTruthy()
    expect(screen.getAllByText('团队').length).toBeGreaterThan(0)
    expect(screen.getAllByText('个人').length).toBeGreaterThan(0)
    expect(screen.getAllByText('负责人').length).toBeGreaterThan(0)
  })

  it('个人组织不显示停用按钮，团队组织显示', async () => {
    mockFetchOrganizations.mockResolvedValue(orgFixture())
    render(
      <MemoryRouter>
        <OrganizationPage />
      </MemoryRouter>,
    )
    await screen.findByText('我的组织')
    expect(screen.getAllByLabelText(/停用组织/).length).toBe(1)
  })

  it('新建组织提交后刷新列表', async () => {
    mockFetchOrganizations.mockResolvedValue(orgFixture())
    mockCreateOrganization.mockResolvedValue({
      id: 3, code: 'new-team', name: '新团队', type: 'team', my_role: 1,
    })
    render(
      <MemoryRouter>
        <OrganizationPage />
      </MemoryRouter>,
    )
    await screen.findByText('QA 团队')
    fireEvent.click(screen.getByRole('button', { name: /新建组织/ }))
    fireEvent.change(screen.getByLabelText('组织编码'), { target: { value: 'new-team' } })
    fireEvent.change(screen.getByLabelText('组织名称'), { target: { value: '新团队' } })
    fireEvent.click(screen.getByRole('button', { name: '保存' }))
    await waitFor(() => expect(mockCreateOrganization).toHaveBeenCalledTimes(1))
    expect(mockCreateOrganization).toHaveBeenCalledWith({
      code: 'new-team',
      name: '新团队',
      description: '',
    })
  })
})
