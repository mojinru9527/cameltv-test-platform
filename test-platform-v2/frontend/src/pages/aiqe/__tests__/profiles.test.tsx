import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const api = vi.hoisted(() => ({
  listProfiles: vi.fn(),
  createProfile: vi.fn(),
  approveProfile: vi.fn(),
}))

vi.mock('@/api/aiqeConsole', () => ({
  listProfiles: api.listProfiles,
  createProfile: api.createProfile,
  approveProfile: api.approveProfile,
}))

const { default: ProfilesPage } = await import('@/pages/aiqe/profiles')

const PENDING = {
  id: 'p1',
  name: '本地隔离基线',
  purpose: 'core_isolated',
  version: 1,
  approval_status: 'pending',
  checksum: 'a'.repeat(64),
  owner_id: 1,
  frozen: false,
}

const APPROVED = {
  ...PENDING,
  id: 'p2',
  name: '已冻结配置',
  approval_status: 'approved',
  frozen: true,
}

function renderPage() {
  return render(
    <MemoryRouter>
      <ProfilesPage />
    </MemoryRouter>,
  )
}

describe('Execution Profiles 页面（batch-337）', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.listProfiles.mockResolvedValue([PENDING, APPROVED])
  })

  it('渲染列表并对待审批项发起审批', async () => {
    api.approveProfile.mockResolvedValue({ ...PENDING, approval_status: 'approved', frozen: true })

    renderPage()

    expect(await screen.findByText('本地隔离基线')).toBeTruthy()
    expect(screen.getByText('已冻结')).toBeTruthy()

    fireEvent.click(screen.getByRole('button', { name: '审批' }))

    await waitFor(() => expect(api.approveProfile).toHaveBeenCalledWith('p1'))
    await waitFor(() => expect(screen.getAllByText('已冻结').length).toBe(2))
    expect(api.listProfiles).toHaveBeenCalledTimes(1)
  })

  it('创建 Profile 后追加到列表', async () => {
    api.createProfile.mockResolvedValue({
      ...PENDING,
      id: 'p3',
      name: '新配置',
    })

    renderPage()
    await screen.findByText('本地隔离基线')

    fireEvent.change(screen.getByLabelText('Profile 名称'), { target: { value: '新配置' } })
    fireEvent.click(screen.getByRole('button', { name: '创建' }))

    await waitFor(() =>
      expect(api.createProfile).toHaveBeenCalledWith({ name: '新配置', purpose: 'core_isolated' }),
    )
    expect(await screen.findByText('新配置')).toBeTruthy()
  })

  it('已冻结行禁用审批按钮', async () => {
    renderPage()
    await screen.findByText('已冻结配置')

    const buttons = screen.getAllByRole('button', { name: /审批|已审批/ })
    expect(buttons.some((button) => (button as HTMLButtonElement).disabled)).toBe(true)
  })
})
