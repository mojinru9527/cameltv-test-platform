import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useAuthStore } from '@/stores/auth'

const api = vi.hoisted(() => ({
  fetchAvTasks: vi.fn(),
  fetchAvTask: vi.fn(),
  triggerAvCheck: vi.fn(),
}))

const toast = vi.hoisted(() => ({
  info: vi.fn(),
  success: vi.fn(),
  error: vi.fn(),
  warning: vi.fn(),
}))

vi.mock('sonner', () => ({ toast }))

vi.mock('@/api/avcheck', () => ({
  fetchAvTasks: (...args: unknown[]) => api.fetchAvTasks(...args),
  fetchAvTask: (...args: unknown[]) => api.fetchAvTask(...args),
  triggerAvCheck: (...args: unknown[]) => api.triggerAvCheck(...args),
  createAvTask: vi.fn(),
  deleteAvTask: vi.fn(),
  updateAvTask: vi.fn(),
  fetchAvMeasurementTemplates: vi.fn().mockResolvedValue([]),
  createAvMeasurement: vi.fn(),
  updateAvMeasurement: vi.fn(),
  deleteAvMeasurement: vi.fn(),
}))

import SpecialPage, { PROTOCOL_MAP } from './index'

const idleTask = {
  id: 7,
  task_id: 'AV-B60-001',
  name: 'Batch 60 体育直播流检测',
  stream_url: 'https://sports.example.test/live.m3u8',
  protocol: 'HLS',
  status: 'idle',
  last_result: '{}',
  creator_id: 1,
  creator_name: '管理员',
  metrics: [],
  measurements: [],
  created_at: '2026-08-01T00:00:00Z',
  updated_at: '2026-08-01T00:00:00Z',
}

describe('音视频后台探测反馈', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    HTMLElement.prototype.scrollIntoView = vi.fn()
    useAuthStore.setState({ permissions: ['*'] })
    api.fetchAvTasks.mockResolvedValue({ total: 1, items: [idleTask], page: 1, page_size: 20 })
    api.triggerAvCheck.mockResolvedValue({ ...idleTask, status: 'running' })
    api.fetchAvTask.mockResolvedValue({ ...idleTask, status: 'done' })
  })

  it('先提示后台启动，读取终态后才提示检测完成', async () => {
    render(<SpecialPage />)

    expect(await screen.findByText(idleTask.name)).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: '触发' }))

    await waitFor(() => expect(api.fetchAvTask).toHaveBeenCalledWith(7, expect.any(AbortSignal)))
    expect(toast.info).toHaveBeenCalledWith('检测已启动，正在后台执行')
    expect(toast.success).toHaveBeenCalledWith('检测已完成')
    expect(toast.info.mock.invocationCallOrder[0]).toBeLessThan(
      toast.success.mock.invocationCallOrder[0],
    )
  })

  it('详情抽屉为指标与长流地址保留可读宽度', async () => {
    render(<SpecialPage />)

    expect(await screen.findByText(idleTask.name)).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: '详情' }))

    const dialog = await screen.findByRole('dialog', { name: '检测详情' })
    expect(dialog.className).toContain('data-[side=right]:sm:max-w-2xl')
    const streamValue = await screen.findByText(idleTask.stream_url)
    expect(streamValue.className).toContain('break-all')
  })

  it('支持按真实 HTTP 媒体地址标记协议', () => {
    expect(Object.keys(PROTOCOL_MAP)).toEqual(expect.arrayContaining(['HTTP', 'HTTPS']))
  })

  it('空态使用与主操作一致的新建检测文案', async () => {
    api.fetchAvTasks.mockResolvedValue({ total: 0, items: [], page: 1, page_size: 20 })

    render(<SpecialPage />)

    expect(await screen.findByText('点击「新建检测」创建音视频质量检测')).toBeTruthy()
  })
})
