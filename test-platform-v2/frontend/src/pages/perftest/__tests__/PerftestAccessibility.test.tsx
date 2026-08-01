import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
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

  it('wraps the four navigation tabs into two columns on mobile', async () => {
    render(
      <MemoryRouter initialEntries={['/perftest?tab=device']}>
        <PerfTestPage />
      </MemoryRouter>,
    )

    const tablist = screen.getByRole('tablist')
    expect(tablist.className).toContain('grid-cols-2')
    expect(tablist.className).toContain('sm:grid-cols-4')
    expect(tablist.className).toContain('group-data-[orientation=horizontal]/tabs:h-auto')
    expect(screen.getByRole('tab', { name: '设备与采集' }).className).toContain('min-h-11')
    expect(await screen.findByText('未检测到设备')).toBeTruthy()
  })

  it('shows a persistent truthful unavailable state when SoloX is missing and recovers on retry', async () => {
    api.fetchDevices
      .mockRejectedValueOnce({
        response: {
          status: 503,
          data: { msg: 'SoloX 未安装，真实性能采集不可用' },
        },
      })
      .mockResolvedValueOnce([])

    render(
      <MemoryRouter initialEntries={['/perftest?tab=device']}>
        <PerfTestPage />
      </MemoryRouter>,
    )

    const alert = await screen.findByRole('alert')
    expect(alert.textContent).toContain('真实性能采集不可用')
    expect(alert.textContent).toContain('不会生成模拟数据')
    expect(screen.queryByText('未检测到设备')).toBeNull()

    fireEvent.click(screen.getByRole('button', { name: '重新检测采集器' }))

    expect(await screen.findByText('未检测到设备')).toBeTruthy()
    expect(screen.queryByRole('alert')).toBeNull()
    expect(api.fetchDevices).toHaveBeenCalledTimes(2)
  })
})
