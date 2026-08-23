import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const api = vi.hoisted(() => ({
  fetchOpsDeployments: vi.fn(),
  fetchOpsDeploymentEvents: vi.fn(),
  publishOpsDeployment: vi.fn(),
  rollbackOpsDeployment: vi.fn(),
  backupOpsDeployment: vi.fn(),
  submitOpsRelease: vi.fn(),
}))

vi.mock('@/api/opsReleases', () => ({
  fetchOpsDeployments: (...args: unknown[]) => api.fetchOpsDeployments(...args),
  fetchOpsDeploymentEvents: (...args: unknown[]) => api.fetchOpsDeploymentEvents(...args),
  publishOpsDeployment: (...args: unknown[]) => api.publishOpsDeployment(...args),
  rollbackOpsDeployment: (...args: unknown[]) => api.rollbackOpsDeployment(...args),
  backupOpsDeployment: (...args: unknown[]) => api.backupOpsDeployment(...args),
  submitOpsRelease: (...args: unknown[]) => api.submitOpsRelease(...args),
}))

import OperationsReleasePage from './index'

describe('operations release page', () => {
  beforeEach(() => {
    api.fetchOpsDeployments.mockReset().mockResolvedValue([])
    api.fetchOpsDeploymentEvents.mockReset().mockResolvedValue([])
    api.publishOpsDeployment.mockReset().mockResolvedValue({ action: 'publish', ok: true, summary: 'deployed', logs: '' })
    api.rollbackOpsDeployment.mockReset().mockResolvedValue({ action: 'rollback', ok: true, summary: 'rolled back', logs: '' })
    api.backupOpsDeployment.mockReset().mockResolvedValue({ action: 'backup', ok: true, summary: 'backup captured', logs: '' })
    api.submitOpsRelease.mockReset().mockResolvedValue({ action: 'submit', ok: true, summary: 'registered', logs: '' })
  })

  it('shows the release platform header with submit action and empty persisted state', async () => {
    render(<MemoryRouter><OperationsReleasePage /></MemoryRouter>)

    expect(await screen.findByText('暂无已持久化发布记录')).toBeTruthy()
    expect(await screen.findByRole('button', { name: /提交发布登记/ })).toBeTruthy()
    expect(api.fetchOpsDeployments).toHaveBeenCalledTimes(1)
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
    expect(alert.textContent).toContain('TENCENT_EXECUTOR')
    expect(screen.queryByText('release-control state store is not configured')).toBeNull()
  })

  it('shows publish/rollback/backup actions for a production-verified deployment', async () => {
    api.fetchOpsDeployments.mockResolvedValue([
      { id: 'dep-prod', release_id: 'rel-prod-1', manifest_sha256: 'b'.repeat(64), environment: 'production', state: 'PROD_OBSERVING', created_at: '2026-08-22T00:00:00+00:00' },
    ])

    render(<MemoryRouter><OperationsReleasePage /></MemoryRouter>)

    const record = await screen.findByRole('button', { name: '查看发布记录 rel-prod-1' })
    fireEvent.click(record)
    expect(await screen.findByRole('button', { name: /发布到生产/ })).toBeTruthy()
    expect(await screen.findByRole('button', { name: /回滚/ })).toBeTruthy()
    expect(await screen.findByRole('button', { name: /备份/ })).toBeTruthy()
    expect(api.fetchOpsDeploymentEvents).toHaveBeenCalled()
  })
})
