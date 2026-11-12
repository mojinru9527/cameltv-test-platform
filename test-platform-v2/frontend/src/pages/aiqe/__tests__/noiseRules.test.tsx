import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const api = vi.hoisted(() => ({
  listNoiseRules: vi.fn(),
  createNoiseRule: vi.fn(),
  renewNoiseRule: vi.fn(),
  deleteNoiseRule: vi.fn(),
}))

vi.mock('@/api/aiqeConsole', () => ({
  listNoiseRules: api.listNoiseRules,
  createNoiseRule: api.createNoiseRule,
  renewNoiseRule: api.renewNoiseRule,
  deleteNoiseRule: api.deleteNoiseRule,
}))

const { default: NoiseRulesPage } = await import('@/pages/aiqe/noise-rules')

const soon = new Date(Date.now() + 2 * 86_400_000).toISOString()
const past = new Date(Date.now() - 86_400_000).toISOString()

const ACTIVE = {
  id: 1,
  pattern: '广告弹窗',
  action: 'suppress',
  scope: 'run',
  expires_at: soon,
  status: 'active',
  effective: true,
}
const EXPIRED = {
  ...ACTIVE,
  id: 2,
  pattern: '旧规则',
  expires_at: past,
  effective: false,
}

function renderPage() {
  return render(
    <MemoryRouter>
      <NoiseRulesPage />
    </MemoryRouter>,
  )
}

describe('噪音规则页面（batch-338）', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.listNoiseRules.mockResolvedValue([ACTIVE, EXPIRED])
  })

  it('过期规则标红并显示剩余天数', async () => {
    renderPage()

    expect(await screen.findByText('广告弹窗')).toBeTruthy()
    expect(screen.getByText('（剩 2 天）', { exact: false })).toBeTruthy()
    expect(screen.getByText('（已过期）', { exact: false })).toBeTruthy()
    expect(screen.getByText('已过期')).toBeTruthy()
  })

  it('续期调用 API 并更新到期时间', async () => {
    const renewed = { ...ACTIVE, expires_at: new Date(Date.now() + 90 * 86_400_000).toISOString() }
    api.renewNoiseRule.mockResolvedValue(renewed)

    renderPage()
    await screen.findByText('广告弹窗')

    fireEvent.click(screen.getAllByRole('button', { name: '续期' })[0])

    await waitFor(() => expect(api.renewNoiseRule).toHaveBeenCalledWith(1))
    expect(await screen.findByText('（剩 90 天）', { exact: false })).toBeTruthy()
  })

  it('创建规则后追加到列表', async () => {
    api.createNoiseRule.mockResolvedValue({ ...ACTIVE, id: 3, pattern: '新规则' })

    renderPage()
    await screen.findByText('广告弹窗')

    fireEvent.change(screen.getByLabelText('规则 pattern'), { target: { value: '新规则' } })
    fireEvent.click(screen.getByRole('button', { name: '创建' }))

    await waitFor(() =>
      expect(api.createNoiseRule).toHaveBeenCalledWith({
        pattern: '新规则',
        action: 'suppress',
        scope: 'run',
      }),
    )
    expect(await screen.findByText('新规则')).toBeTruthy()
  })
})
