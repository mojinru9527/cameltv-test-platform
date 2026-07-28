import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const api = vi.hoisted(() => ({
  fetchDevices: vi.fn(),
  fetchSessions: vi.fn(),
}))

vi.mock('@/api/perftest', () => ({
  fetchDevices: (...args: unknown[]) => api.fetchDevices(...args),
  fetchSessions: (...args: unknown[]) => api.fetchSessions(...args),
  fetchSession: vi.fn(),
  createSession: vi.fn(),
  deleteSession: vi.fn(),
  startSession: vi.fn(),
  stopSession: vi.fn(),
  fetchReport: vi.fn(),
  compareSessions: vi.fn(),
}))

vi.mock('@/hooks/usePerfWebSocket', () => ({
  usePerfWebSocket: () => ({ mode: 'idle', reconnectCount: 0 }),
}))

import PerfTestPage from '../index'

describe('performance page icon actions', () => {
  beforeEach(() => {
    api.fetchDevices.mockReset().mockResolvedValue([])
    api.fetchSessions.mockReset().mockResolvedValue({ items: [], total: 0 })
  })

  it('names the device refresh action', async () => {
    render(
      <MemoryRouter initialEntries={['/perftest?tab=device']}>
        <PerfTestPage />
      </MemoryRouter>,
    )

    expect(screen.getByRole('button', { name: '刷新设备列表' })).toBeTruthy()
    expect(await screen.findByText('未检测到设备')).toBeTruthy()
  })

  it('names the session refresh action', async () => {
    render(
      <MemoryRouter initialEntries={['/perftest?tab=history']}>
        <PerfTestPage />
      </MemoryRouter>,
    )

    expect(screen.getByRole('button', { name: '刷新采集记录' })).toBeTruthy()
    expect(await screen.findByText('暂无采集记录')).toBeTruthy()
  })
})
