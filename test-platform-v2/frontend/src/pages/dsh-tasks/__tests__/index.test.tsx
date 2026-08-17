import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'

const mockFetchDshTasks = vi.fn()
const mockFetchDshHealth = vi.fn()
const mockFetchDshTask = vi.fn()
const mockCreateDshTask = vi.fn()
const mockCancelDshTask = vi.fn()

vi.mock('@/hooks/useDocumentTitle', () => ({ useDocumentTitle: vi.fn() }))
vi.mock('@/api/dshTasks', () => ({
  fetchDshTasks: (...args: unknown[]) => mockFetchDshTasks(...args),
  fetchDshHealth: (...args: unknown[]) => mockFetchDshHealth(...args),
  fetchDshTask: (...args: unknown[]) => mockFetchDshTask(...args),
  createDshTask: (...args: unknown[]) => mockCreateDshTask(...args),
  cancelDshTask: (...args: unknown[]) => mockCancelDshTask(...args),
}))
vi.mock('@/stores/auth', () => ({
  useAuthStore: () => ({ hasPerm: () => true }),
}))
vi.mock('sonner', () => ({ toast: { success: vi.fn(), error: vi.fn() } }))

import DshTasksPage from '../index'

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
  vi.useRealTimers()
})

function taskFixture(overrides: Record<string, any> = {}): Record<string, any> {
  return {
    id: 1,
    project_id: 1,
    task: '为登录模块生成用例并跑回归',
    status: 'pending',
    mode: 'single',
    team_json: {},
    output_text: '',
    session_dir: '',
    error: '',
    operator_id: 1,
    created_at: '2026-08-17T10:00:00',
    started_at: null,
    finished_at: null,
    ...overrides,
  }
}

describe('DSH 任务页（Batch 191 团队模式）', () => {
  it('列表渲染 mode 徽标：团队/标准', async () => {
    mockFetchDshTasks.mockResolvedValue({ items: [
      taskFixture({ id: 1, mode: 'team' }),
      taskFixture({ id: 2, mode: 'single' }),
    ], total: 2, page: 1, page_size: 50 })
    mockFetchDshHealth.mockResolvedValue({ available: true, reason: '' })
    render(
      <MemoryRouter>
        <DshTasksPage />
      </MemoryRouter>,
    )
    expect(await screen.findByText('为登录模块生成用例并跑回归')).toBeTruthy()
    expect(screen.getByText('团队')).toBeTruthy()
    expect(screen.getByText('标准')).toBeTruthy()
  })

  it('模式切换：默认标准无批次下拉；切团队出现批次下拉；切回隐藏', async () => {
    mockFetchDshTasks.mockResolvedValue({ items: [], total: 0, page: 1, page_size: 50 })
    mockFetchDshHealth.mockResolvedValue({ available: true, reason: '' })
    render(
      <MemoryRouter>
        <DshTasksPage />
      </MemoryRouter>,
    )
    // 打开新建 Dialog
    fireEvent.click(await screen.findByRole('button', { name: /新建任务/ }))
    // 默认标准模式 → 无批次下拉
    expect(screen.getByLabelText('任务模式')).toBeTruthy()
    expect(screen.queryByLabelText('批次模式')).toBeNull()
    // 切团队模式 → 出现批次下拉
    fireEvent.click(screen.getByLabelText('任务模式'))
    fireEvent.click(await screen.findByRole('option', { name: /团队模式/ }))
    expect(await screen.findByLabelText('批次模式')).toBeTruthy()
    // 切回标准 → 隐藏批次下拉
    fireEvent.click(screen.getByLabelText('任务模式'))
    fireEvent.click(await screen.findByRole('option', { name: /标准模式/ }))
    await waitFor(() => expect(screen.queryByLabelText('批次模式')).toBeNull())
  })

  it('提交团队任务带 mode 与 batch_mode', async () => {
    mockFetchDshTasks.mockResolvedValue({ items: [], total: 0, page: 1, page_size: 50 })
    mockFetchDshHealth.mockResolvedValue({ available: true, reason: '' })
    mockCreateDshTask.mockResolvedValue(taskFixture({ id: 9, mode: 'team' }))
    render(
      <MemoryRouter>
        <DshTasksPage />
      </MemoryRouter>,
    )
    fireEvent.click(await screen.findByRole('button', { name: /新建任务/ }))
    fireEvent.change(screen.getByLabelText('任务描述'), { target: { value: '跑回归' } })
    fireEvent.click(screen.getByLabelText('任务模式'))
    fireEvent.click(await screen.findByRole('option', { name: /团队模式/ }))
    await screen.findByLabelText('批次模式')
    // 默认批次 full
    fireEvent.click(screen.getByRole('button', { name: /提交/ }))
    await waitFor(() => expect(mockCreateDshTask).toHaveBeenCalledTimes(1))
    expect(mockCreateDshTask).toHaveBeenCalledWith('跑回归', { batch_mode: 'full' }, 'team')
  })

  it('详情 running 团队任务轮询刷新，卸载后无残留定时器', async () => {
    vi.useFakeTimers()
    mockFetchDshTasks.mockResolvedValue({ items: [
      taskFixture({ id: 1, mode: 'team', status: 'running' }),
    ], total: 1, page: 1, page_size: 50 })
    mockFetchDshHealth.mockResolvedValue({ available: true, reason: '' })
    const { unmount } = render(
      <MemoryRouter>
        <DshTasksPage />
      </MemoryRouter>,
    )
    // 打开详情（点击行）
    const row = await screen.findByText('为登录模块生成用例并跑回归')
    fireEvent.click(row)
    await waitFor(() => expect(mockFetchDshTask).toHaveBeenCalledTimes(1))

    // 前进一个轮询周期 → 应再次拉取详情
    const before = mockFetchDshTask.mock.calls.length
    await vi.advanceTimersByTimeAsync(3000)
    expect(mockFetchDshTask.mock.calls.length).toBeGreaterThan(before)

    // 卸载 → 无残留定时器
    unmount()
    expect(vi.getTimerCount()).toBe(0)
  })

  it('终态（success）团队任务不轮询', async () => {
    vi.useFakeTimers()
    mockFetchDshTasks.mockResolvedValue({ items: [
      taskFixture({ id: 1, mode: 'team', status: 'success' }),
    ], total: 1, page: 1, page_size: 50 })
    mockFetchDshHealth.mockResolvedValue({ available: true, reason: '' })
    mockFetchDshTask.mockResolvedValue(taskFixture({ id: 1, mode: 'team', status: 'success' }))
    const { unmount } = render(
      <MemoryRouter>
        <DshTasksPage />
      </MemoryRouter>,
    )
    fireEvent.click(await screen.findByText('为登录模块生成用例并跑回归'))
    await waitFor(() => expect(mockFetchDshTask).toHaveBeenCalledTimes(1))
    const before = mockFetchDshTask.mock.calls.length
    await vi.advanceTimersByTimeAsync(9000)
    expect(mockFetchDshTask.mock.calls.length).toBe(before)  // 不轮询
    unmount()
    expect(vi.getTimerCount()).toBe(0)
  })
})
