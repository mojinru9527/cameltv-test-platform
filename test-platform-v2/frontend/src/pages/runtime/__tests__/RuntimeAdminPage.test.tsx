import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const mocks = vi.hoisted(() => ({
  fetchWorkers: vi.fn(),
  fetchWorkflows: vi.fn(),
  fetchApprovals: vi.fn(),
  fetchSecretRefs: vi.fn(),
  fetchPolicyProfiles: vi.fn(),
}))

vi.mock('@/api/runtime', async (importOriginal) => {
  const original = await importOriginal<typeof import('@/api/runtime')>()
  return {
    ...original,
    fetchWorkers: (...args: unknown[]) => mocks.fetchWorkers(...args),
    fetchWorkflows: (...args: unknown[]) => mocks.fetchWorkflows(...args),
    fetchApprovals: (...args: unknown[]) => mocks.fetchApprovals(...args),
    fetchSecretRefs: (...args: unknown[]) => mocks.fetchSecretRefs(...args),
    fetchPolicyProfiles: (...args: unknown[]) => mocks.fetchPolicyProfiles(...args),
  }
})

const { default: RuntimeAdminPage } = await import('@/pages/runtime')

describe('RuntimeAdminPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mocks.fetchWorkers
      .mockRejectedValueOnce(new Error('Worker 列表暂不可用'))
      .mockResolvedValue({ items: [] })
    mocks.fetchWorkflows.mockResolvedValue({ items: [], total: 0, page: 1, page_size: 50 })
    mocks.fetchApprovals.mockResolvedValue({ items: [] })
    mocks.fetchSecretRefs.mockResolvedValue({ items: [] })
    mocks.fetchPolicyProfiles.mockResolvedValue({ items: [] })
  })

  it('shows a retryable error instead of silently rendering empty data', async () => {
    render(
      <MemoryRouter>
        <RuntimeAdminPage />
      </MemoryRouter>,
    )

    expect((await screen.findByRole('alert')).textContent).toContain('Worker 列表暂不可用')
    fireEvent.click(screen.getByRole('button', { name: '重新检查' }))

    await waitFor(() => expect(mocks.fetchWorkers).toHaveBeenCalledTimes(2))
    expect(await screen.findByText(/尚未发现 Worker/)).toBeTruthy()
  })
})
