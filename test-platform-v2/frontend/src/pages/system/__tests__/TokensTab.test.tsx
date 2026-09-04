import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useAuthStore } from '@/stores/auth'

const mocks = vi.hoisted(() => ({
  fetchTokens: vi.fn(),
  createToken: vi.fn(),
  updateToken: vi.fn(),
  deleteToken: vi.fn(),
}))

vi.mock('@/api/token', () => mocks)

const { default: TokensTab } = await import('../TokensTab')

describe('TokensTab Worker onboarding', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useAuthStore.setState({ permissions: ['*'] })
    mocks.fetchTokens.mockResolvedValue([])
    mocks.createToken.mockResolvedValue({
      id: 7,
      name: 'Test5 Worker',
      token: 'tpat_test_only',
      token_prefix: 'tpat_test_on',
      scopes: ['workers:register'],
    })
  })

  it('preselects Worker purpose and shows one-time startup configuration', async () => {
    render(
      <MemoryRouter initialEntries={['/system?tab=tokens&purpose=worker']}>
        <TokensTab />
      </MemoryRouter>,
    )

    fireEvent.click(screen.getByRole('button', { name: '新建 Token' }))
    expect(screen.getByRole('combobox', { name: 'Token 用途' }).textContent).toContain('Worker 执行节点')
    fireEvent.change(screen.getByRole('textbox', { name: 'Token 名称' }), {
      target: { value: 'Test5 Worker' },
    })
    fireEvent.click(screen.getByRole('button', { name: '创建' }))

    await waitFor(() => expect(mocks.createToken).toHaveBeenCalledWith({
      name: 'Test5 Worker',
      scopes: ['workers:register'],
    }))
    expect(await screen.findByText('Worker 启动配置')).toBeTruthy()
    expect(screen.getAllByText(/tpat_test_only/).length).toBeGreaterThan(0)
    expect(screen.getByText(/BACKEND_URL=http:\/\/localhost:3000\/api\/v2/)).toBeTruthy()
  })
})
