import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'

// Radix Select 在 jsdom 需要 scrollIntoView（jsdom 未实现，打开下拉时崩溃）
if (!Element.prototype.scrollIntoView) {
  Element.prototype.scrollIntoView = () => undefined
}

const mockFetchDshTasks = vi.fn()
const mockFetchDshHealth = vi.fn()
const mockFetchDshTask = vi.fn()
const mockCreateDshTask = vi.fn()
const mockCancelDshTask = vi.fn()
const mockFetchDshModelPool = vi.fn()

vi.mock('@/hooks/useDocumentTitle', () => ({ useDocumentTitle: vi.fn() }))
vi.mock('@/api/dshTasks', () => ({
  fetchDshTasks: (...args: unknown[]) => mockFetchDshTasks(...args),
  fetchDshHealth: (...args: unknown[]) => mockFetchDshHealth(...args),
  fetchDshTask: (...args: unknown[]) => mockFetchDshTask(...args),
  createDshTask: (...args: unknown[]) => mockCreateDshTask(...args),
  cancelDshTask: (...args: unknown[]) => mockCancelDshTask(...args),
  fetchDshModelPool: (...args: unknown[]) => mockFetchDshModelPool(...args),
}))
vi.mock('@/stores/auth', () => ({
  // QA 打回 P2：useAuthStore 是 selector 式 hook，mock 必须应用 selector（仓库既有范式）
  useAuthStore: (selector: (state: { hasPerm: (p: string) => boolean }) => unknown) =>
    selector({ hasPerm: () => true }),
}))
vi.mock('sonner', () => ({ toast: { success: vi.fn(), error: vi.fn() } }))

import DshTasksPage from '../index'

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
  vi.useRealTimers()
})

/** 默认 model-pool mock（未配置池 → 前端不渲染模型下拉） */
function mockDefaultPool() {
  mockFetchDshModelPool.mockResolvedValue({ models: [], default_model: 'deepseek-v4-flash', pool_configured: false })
}

/** 配置了池的 model-pool mock（前端渲染模型下拉） */
function mockConfiguredPool() {
  mockFetchDshModelPool.mockResolvedValue({
    models: ['deepseek-v4-flash', 'deepseek-v4-pro'],
    default_model: 'deepseek-v4-flash',
    pool_configured: true,
  })
}

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
      { ...taskFixture({ id: 2, mode: 'single' }), task: '标准单任务文本' },
    ], total: 2, page: 1, page_size: 50 })
    mockFetchDshHealth.mockResolvedValue({ available: true, reason: '' })
    mockDefaultPool()
    render(
      <MemoryRouter>
        <DshTasksPage />
      </MemoryRouter>,
    )
    expect(await screen.findByText('为登录模块生成用例并跑回归')).toBeTruthy()
    expect(screen.getByText('标准单任务文本')).toBeTruthy()
    expect(screen.getByText('团队')).toBeTruthy()
    expect(screen.getByText('标准')).toBeTruthy()
  })

  it('模式切换：默认标准无批次下拉；切团队出现批次下拉；切回隐藏', async () => {
    mockFetchDshTasks.mockResolvedValue({ items: [], total: 0, page: 1, page_size: 50 })
    mockFetchDshHealth.mockResolvedValue({ available: true, reason: '' })
    mockDefaultPool()
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

  it('提交团队任务带 mode、batch_mode 与 team_kind', async () => {
    mockFetchDshTasks.mockResolvedValue({ items: [], total: 0, page: 1, page_size: 50 })
    mockFetchDshHealth.mockResolvedValue({ available: true, reason: '' })
    mockDefaultPool()
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
    // 默认批次 full + 团队视角 dev
    fireEvent.click(screen.getByRole('button', { name: /提交/ }))
    await waitFor(() => expect(mockCreateDshTask).toHaveBeenCalledTimes(1))
    expect(mockCreateDshTask).toHaveBeenCalledWith('跑回归', { batch_mode: 'full', team_kind: 'dev' }, 'team')
  })

  it('团队视角切换到测试视角后提交带 team_kind=tester', async () => {
    mockFetchDshTasks.mockResolvedValue({ items: [], total: 0, page: 1, page_size: 50 })
    mockFetchDshHealth.mockResolvedValue({ available: true, reason: '' })
    mockDefaultPool()
    mockCreateDshTask.mockResolvedValue(taskFixture({ id: 10, mode: 'team' }))
    render(
      <MemoryRouter>
        <DshTasksPage />
      </MemoryRouter>,
    )
    fireEvent.click(await screen.findByRole('button', { name: /新建任务/ }))
    fireEvent.change(screen.getByLabelText('任务描述'), { target: { value: '为登录模块设计用例并执行' } })
    fireEvent.click(screen.getByLabelText('任务模式'))
    fireEvent.click(await screen.findByRole('option', { name: /团队模式/ }))
    await screen.findByLabelText('团队视角')
    fireEvent.click(screen.getByLabelText('团队视角'))
    fireEvent.click(await screen.findByRole('option', { name: /测试视角/ }))
    fireEvent.click(screen.getByRole('button', { name: /提交/ }))
    await waitFor(() => expect(mockCreateDshTask).toHaveBeenCalledTimes(1))
    expect(mockCreateDshTask).toHaveBeenCalledWith(
      '为登录模块设计用例并执行',
      { batch_mode: 'full', team_kind: 'tester' },
      'team',
    )
  })

  it('模型池配置后渲染模型下拉，选择模型随提交携带', async () => {
    mockFetchDshTasks.mockResolvedValue({ items: [], total: 0, page: 1, page_size: 50 })
    mockFetchDshHealth.mockResolvedValue({ available: true, reason: '' })
    mockConfiguredPool()
    mockCreateDshTask.mockResolvedValue(taskFixture({ id: 11, mode: 'single' }))
    render(
      <MemoryRouter>
        <DshTasksPage />
      </MemoryRouter>,
    )
    fireEvent.click(await screen.findByRole('button', { name: /新建任务/ }))
    fireEvent.change(screen.getByLabelText('任务描述'), { target: { value: '单任务' } })
    // 模型下拉出现（池已配置）
    expect(await screen.findByLabelText('模型')).toBeTruthy()
    fireEvent.click(screen.getByLabelText('模型'))
    fireEvent.click(await screen.findByRole('option', { name: 'deepseek-v4-pro' }))
    fireEvent.click(screen.getByRole('button', { name: /提交/ }))
    await waitFor(() => expect(mockCreateDshTask).toHaveBeenCalledTimes(1))
    // 标准模式：createDshTask(task, params)（mode 默认 single）
    expect(mockCreateDshTask).toHaveBeenCalledWith('单任务', { model: 'deepseek-v4-pro' })
  })

  it('详情 running 团队任务轮询刷新，卸载后无残留定时器', async () => {
    // 列表渲染在真实 timers 下完成（findByText 依赖 waitFor），随后切 fake timers。
    // 列表任务用 pending：避免列表页 hasRunning 指数退避轮询干扰（Batch 178 既有逻辑），
    // 详情数据由 fetchDshTask mock 返回 running → 仅详情轮询 setInterval 存在。
    mockFetchDshTasks.mockResolvedValue({ items: [
      taskFixture({ id: 1, mode: 'team', status: 'pending' }),
    ], total: 1, page: 1, page_size: 50 })
    mockFetchDshHealth.mockResolvedValue({ available: true, reason: '' })
    mockDefaultPool()
    mockFetchDshTask.mockResolvedValue(taskFixture({ id: 1, mode: 'team', status: 'running' }))
    const { unmount } = render(
      <MemoryRouter>
        <DshTasksPage />
      </MemoryRouter>,
    )
    const row = await screen.findByText('为登录模块生成用例并跑回归')
    vi.useFakeTimers()

    // 打开详情（点击行）：useAbortableEffect 经 queueMicrotask 触发 → flush 微任务后断言
    fireEvent.click(row)
    await vi.advanceTimersByTimeAsync(0)
    expect(mockFetchDshTask).toHaveBeenCalledTimes(1)
    expect(vi.getTimerCount()).toBe(1) // 仅详情轮询 interval

    // 前进一个轮询周期 → 应再次拉取详情
    const before = mockFetchDshTask.mock.calls.length
    await vi.advanceTimersByTimeAsync(3000)
    expect(mockFetchDshTask.mock.calls.length).toBeGreaterThan(before)

    // 卸载 → 无残留定时器
    unmount()
    await vi.advanceTimersByTimeAsync(100)
    expect(vi.getTimerCount()).toBe(0)
  })

  it('终态（success）团队任务不轮询', async () => {
    mockFetchDshTasks.mockResolvedValue({ items: [
      taskFixture({ id: 1, mode: 'team', status: 'pending' }),
    ], total: 1, page: 1, page_size: 50 })
    mockFetchDshHealth.mockResolvedValue({ available: true, reason: '' })
    mockDefaultPool()
    mockFetchDshTask.mockResolvedValue(taskFixture({ id: 1, mode: 'team', status: 'success' }))
    const { unmount } = render(
      <MemoryRouter>
        <DshTasksPage />
      </MemoryRouter>,
    )
    const row = await screen.findByText('为登录模块生成用例并跑回归')
    vi.useFakeTimers()
    fireEvent.click(row)
    await vi.advanceTimersByTimeAsync(0)
    expect(mockFetchDshTask).toHaveBeenCalledTimes(1)
    const before = mockFetchDshTask.mock.calls.length
    await vi.advanceTimersByTimeAsync(9000)
    expect(mockFetchDshTask.mock.calls.length).toBe(before)  // 不轮询
    unmount()
    await vi.advanceTimersByTimeAsync(100)
    expect(vi.getTimerCount()).toBe(0)
  })
})
