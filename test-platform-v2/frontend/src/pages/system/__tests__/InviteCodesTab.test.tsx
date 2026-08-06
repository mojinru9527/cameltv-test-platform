import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

const mockFetchInviteCodes = vi.fn()
const mockCreateInviteCode = vi.fn()
const mockDisableInviteCode = vi.fn()

vi.mock('@/hooks/useDocumentTitle', () => ({ useDocumentTitle: vi.fn() }))
vi.mock('@/api/system', () => ({
  fetchInviteCodes: (...args: unknown[]) => mockFetchInviteCodes(...args),
  createInviteCode: (...args: unknown[]) => mockCreateInviteCode(...args),
  disableInviteCode: (...args: unknown[]) => mockDisableInviteCode(...args),
}))

import InviteCodesTab from '../InviteCodesTab'

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
})

describe('邀请码管理 Tab', () => {
  it('列表展示脱敏邀请码、使用次数与中文状态', async () => {
    mockFetchInviteCodes.mockResolvedValue([
      {
        id: 1,
        code: 'ABCDEF1234',
        created_by: 1,
        created_by_name: 'admin',
        usage_limit: 1,
        used_count: 0,
        expires_at: null,
        status: 1,
        created_at: null,
      },
      {
        id: 2,
        code: 'ZZZZZZ9999',
        created_by: 1,
        created_by_name: 'admin',
        usage_limit: 1,
        used_count: 1,
        expires_at: null,
        status: 1,
        created_at: null,
      },
    ])
    render(<InviteCodesTab />)
    expect(await screen.findByText('****1234')).toBeTruthy()
    expect(screen.getByText('****9999')).toBeTruthy()
    expect(screen.getByText('0 / 1')).toBeTruthy()
    expect(screen.getByText('1 / 1')).toBeTruthy()
    expect(screen.getByText('启用')).toBeTruthy()
    expect(screen.getByText('已用尽')).toBeTruthy()
  })

  it('无邀请码时展示空态与生成入口', async () => {
    mockFetchInviteCodes.mockResolvedValue([])
    render(<InviteCodesTab />)
    expect(await screen.findByText('暂无邀请码')).toBeTruthy()
    expect(screen.getByRole('button', { name: /生成邀请码/ })).toBeTruthy()
  })
})
