import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useAuthStore } from '@/stores/auth'

vi.mock('../UsersTab', () => ({ default: () => <div>用户列表内容</div> }))
vi.mock('../RolesTab', () => ({ default: () => <div>角色列表内容</div> }))
vi.mock('../AuditTab', () => ({ default: () => <div>审计内容</div> }))
vi.mock('../TokensTab', () => ({ default: () => <div>Token 管理内容</div> }))
vi.mock('../InviteCodesTab', () => ({ default: () => <div>邀请码内容</div> }))

const { default: SystemPage } = await import('../index')

describe('SystemPage deep links', () => {
  beforeEach(() => {
    useAuthStore.setState({ permissions: ['*'] })
  })

  it('opens API Token management from the Runtime Worker deep link', () => {
    render(
      <MemoryRouter initialEntries={['/system?tab=tokens&purpose=worker']}>
        <SystemPage />
      </MemoryRouter>,
    )

    expect(screen.getByText('Token 管理内容')).toBeTruthy()
    expect(screen.getByRole('tablist').className).toContain('flex-wrap')
    expect(screen.getByRole('tab', { name: 'API Token' }).className).toContain('h-11')
  })
})
