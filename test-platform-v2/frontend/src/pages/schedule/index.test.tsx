import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { beforeAll, beforeEach, describe, expect, it, vi } from 'vitest'
import { useAuthStore } from '@/stores/auth'

const api = vi.hoisted(() => ({
  fetchSchedules: vi.fn(),
  fetchPlans: vi.fn(),
  createSchedule: vi.fn(),
}))

vi.mock('@/api/schedule', () => ({
  fetchSchedules: (...args: unknown[]) => api.fetchSchedules(...args),
  createSchedule: (...args: unknown[]) => api.createSchedule(...args),
  deleteSchedule: vi.fn(),
  fetchScheduleRuns: vi.fn(),
  triggerSchedule: vi.fn(),
  updateSchedule: vi.fn(),
}))

vi.mock('@/api/testplan', () => ({
  fetchPlans: (...args: unknown[]) => api.fetchPlans(...args),
}))

import SchedulePage from './index'

beforeAll(() => {
  vi.stubGlobal('ResizeObserver', class {
    observe() {}
    unobserve() {}
    disconnect() {}
  })
})

const schedule = {
  id: 1,
  name: '每日回归',
  plan_id: 1,
  plan_name: '接口回归计划',
  cron_expression: '0 9 * * 1-5',
  enabled: true,
  last_run: null,
}

describe('定时任务权限与空状态', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useAuthStore.setState({ permissions: ['schedule:list'] })
    api.fetchSchedules.mockResolvedValue({
      total: 1,
      page: 1,
      page_size: 20,
      items: [schedule],
    })
    api.fetchPlans.mockResolvedValue({ items: [] })
  })

  it('只读用户不能操作创建、更新、删除、触发或启用状态', async () => {
    render(<SchedulePage />)

    expect(await screen.findByText(schedule.name)).toBeTruthy()
    expect(screen.queryByRole('button', { name: '新建调度' })).toBeNull()
    expect(screen.queryByRole('button', { name: '触发' })).toBeNull()
    expect(screen.queryByRole('button', { name: '编辑' })).toBeNull()
    expect(screen.queryByRole('button', { name: '删除' })).toBeNull()
    expect((screen.getByRole('switch') as HTMLButtonElement).disabled).toBe(true)
  })

  it('分页接口 items 为空时展示真实空状态且不向只读用户提供创建入口', async () => {
    api.fetchSchedules.mockResolvedValue({
      total: 0,
      page: 1,
      page_size: 20,
      items: [],
    })

    render(<SchedulePage />)

    expect(await screen.findByText('暂无定时任务')).toBeTruthy()
    expect(screen.queryByRole('table')).toBeNull()
    expect(screen.queryByRole('button', { name: '新建调度' })).toBeNull()
  })

  it('创建时未选择计划显示中文校验文案', async () => {
    useAuthStore.setState({ permissions: ['schedule:list', 'schedule:create'] })
    render(<SchedulePage />)

    fireEvent.click(await screen.findByRole('button', { name: '新建调度' }))
    const dialog = await screen.findByRole('dialog', { name: '新建调度' })
    fireEvent.change(within(dialog).getByPlaceholderText('如：每日回归测试'), {
      target: { value: '每日回归' },
    })
    fireEvent.change(within(dialog).getByPlaceholderText('0 9 * * 1-5'), {
      target: { value: '0 9 * * 1-5' },
    })
    fireEvent.click(within(dialog).getByRole('button', { name: '保存' }))

    expect(await within(dialog).findByText('请选择计划')).toBeTruthy()
    expect(within(dialog).queryByText('Required')).toBeNull()
    await waitFor(() => expect(api.createSchedule).not.toHaveBeenCalled())
  })
})
