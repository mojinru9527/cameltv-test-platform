import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { WorkerHealthTable } from '../WorkerHealthTable'

describe('WorkerHealthTable', () => {
  it('shows capabilities and an actionable recovery state for an offline worker', () => {
    const onRefresh = vi.fn()

    render(
      <WorkerHealthTable
        loading={false}
        workers={[
          {
            id: 1,
            worker_key: 'worker-prod-a',
            name: '生产只读执行节点 A',
            network_zone: 'PROD_RO',
            status: 'OFFLINE',
            version: '1.0',
            machine_identity: 'prod-node-a',
            tags_json: {},
            last_heartbeat_at: '2026-09-03T12:00:00Z',
            registered_at: '2026-09-03T10:00:00Z',
            capabilities: ['HTTP', 'BROWSER'],
          },
        ]}
        onRefresh={onRefresh}
      />,
    )

    expect(screen.getByText('HTTP')).toBeTruthy()
    expect(screen.getByText('BROWSER')).toBeTruthy()
    expect(screen.getByText(/Worker 已停止心跳/)).toBeTruthy()
    expect(screen.queryByRole('button', { name: '排空' })).toBeNull()
    expect(screen.queryByRole('button', { name: '禁用' })).toBeNull()

    fireEvent.click(screen.getByRole('button', { name: '重新检查' }))
    expect(onRefresh).toHaveBeenCalledTimes(1)
  })
})
