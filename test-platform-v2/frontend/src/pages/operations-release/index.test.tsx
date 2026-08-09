import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const api = vi.hoisted(() => ({
  fetchOpsDeployments: vi.fn(),
  fetchOpsDeploymentEvents: vi.fn(),
}))

vi.mock('@/api/opsReleases', () => ({
  fetchOpsDeployments: (...args: unknown[]) => api.fetchOpsDeployments(...args),
  fetchOpsDeploymentEvents: (...args: unknown[]) => api.fetchOpsDeploymentEvents(...args),
}))

import OperationsReleasePage from './index'

describe('operations release page', () => {
  beforeEach(() => {
    api.fetchOpsDeployments.mockReset().mockResolvedValue([])
    api.fetchOpsDeploymentEvents.mockReset().mockResolvedValue([])
  })

  it('shows the truthful production deferred notice and empty persisted state', async () => {
    render(<MemoryRouter><OperationsReleasePage /></MemoryRouter>)

    expect(await screen.findByText('生产发布、生产数据库迁移和外部执行器均未配置。此页面没有发布、审批或回滚操作入口。')).toBeTruthy()
    expect(await screen.findByText('暂无已持久化发布记录')).toBeTruthy()
    expect(api.fetchOpsDeployments).toHaveBeenCalledTimes(1)
    expect(screen.queryByRole('button', { name: /发布|审批|回滚/ })).toBeNull()
  })

  it('loads ordered server events only after selecting a persisted deployment', async () => {
    api.fetchOpsDeployments.mockResolvedValue([
      { id: 'dep-1', release_id: 'b62-test-1', manifest_sha256: 'a'.repeat(64), environment: 'test', state: 'VALIDATED', created_at: '2026-08-02T00:00:00+00:00' },
    ])
    api.fetchOpsDeploymentEvents.mockResolvedValue([
      { sequence: 1, from_state: '', to_state: 'DRAFT', phase: 'register', reason: 'test deployment registered', actor: 'ops', created_at: '2026-08-02T00:00:00+00:00' },
      { sequence: 2, from_state: 'DRAFT', to_state: 'VALIDATED', phase: 'validate', reason: 'state transition to VALIDATED', actor: 'system', created_at: '2026-08-02T00:01:00+00:00' },
    ])

    render(<MemoryRouter><OperationsReleasePage /></MemoryRouter>)

    const record = await screen.findByRole('button', { name: '查看发布记录 b62-test-1' })
    expect(api.fetchOpsDeploymentEvents).not.toHaveBeenCalled()
    fireEvent.click(record)
    expect(await screen.findByText('state transition to VALIDATED')).toBeTruthy()
    expect(api.fetchOpsDeploymentEvents).toHaveBeenCalledTimes(1)
  })

  it('renders the expected unconfigured store as a controlled unavailable state', async () => {
    const error = Object.assign(
      new Error('release-control state store is not configured'),
      { response: { status: 503 } },
    )
    api.fetchOpsDeployments.mockRejectedValue(error)

    render(<MemoryRouter><OperationsReleasePage /></MemoryRouter>)

    expect(await screen.findByText('当前环境未启用发布控制数据源')).toBeTruthy()
    const alert = screen.getByRole('alert')
    expect(alert.textContent).toContain('当前环境未启用发布控制数据源')
    expect(alert.textContent).toContain('未配置不代表服务异常')
    expect(screen.queryByText('release-control state store is not configured')).toBeNull()
  })
})
