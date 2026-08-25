import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter } from 'react-router'
import { useAuthStore } from '@/stores/auth'

const api = vi.hoisted(() => ({
  fetchUiJobs: vi.fn(),
  fetchScripts: vi.fn(),
  fetchRunArtifactBlob: vi.fn(),
  triggerUiJob: vi.fn(),
}))
const environmentApi = vi.hoisted(() => ({ fetchEnvironments: vi.fn() }))

vi.mock('@/api/uitest', () => ({
  fetchUiJobs: (...args: unknown[]) => api.fetchUiJobs(...args),
  fetchScripts: (...args: unknown[]) => api.fetchScripts(...args),
  cancelRun: vi.fn(),
  createUiJob: vi.fn(),
  deleteUiJob: vi.fn(),
  fetchRunArtifacts: vi.fn(),
  fetchRunArtifactBlob: (...args: unknown[]) => api.fetchRunArtifactBlob(...args),
  fetchRunDetail: vi.fn(),
  fetchUiJob: vi.fn(),
  fetchUiRuns: vi.fn(),
  triggerUiJob: (...args: unknown[]) => api.triggerUiJob(...args),
  updateUiJob: vi.fn(),
}))

vi.mock('@/api/environment', () => ({
  fetchEnvironments: (...args: unknown[]) => environmentApi.fetchEnvironments(...args),
}))

import UiTestPage, { ProtectedArtifactMedia } from '../index'

beforeAll(() => {
  vi.stubGlobal('ResizeObserver', class {
    observe() {}
    unobserve() {}
    disconnect() {}
  })
  Object.defineProperty(URL, 'createObjectURL', {
    configurable: true,
    value: vi.fn(() => 'blob:protected-artifact'),
  })
  Object.defineProperty(URL, 'revokeObjectURL', {
    configurable: true,
    value: vi.fn(),
  })
})

describe('UI 自动化页面请求状态', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useAuthStore.setState({ permissions: ['uitest:list', 'uitest:create'] })
    api.fetchUiJobs.mockResolvedValue({ total: 0, items: [], page: 1, page_size: 20 })
    api.fetchScripts.mockResolvedValue(['specs/sports-smoke.spec.ts'])
    api.triggerUiJob.mockResolvedValue({ id: 1, status: 'pending' })
    environmentApi.fetchEnvironments.mockResolvedValue([])
  })

  afterEach(() => cleanup())

  it('列表请求失败时显示可重试错误态而不是空数据', async () => {
    api.fetchUiJobs.mockRejectedValue(new Error('无权访问当前项目'))

    render(<MemoryRouter><UiTestPage /></MemoryRouter>)

    expect(await screen.findByRole('alert')).toBeTruthy()
    expect(screen.getByText('无权访问当前项目')).toBeTruthy()
    expect(screen.getByRole('button', { name: '重新加载' })).toBeTruthy()
    expect(screen.queryByText('暂无 UI 测试任务')).toBeNull()
  })

  it('打开脚本选择器只请求一次脚本列表', async () => {
    render(<MemoryRouter><UiTestPage /></MemoryRouter>)
    await waitFor(() => expect(api.fetchUiJobs).toHaveBeenCalledTimes(1))

    fireEvent.click(screen.getByRole('button', { name: '新建任务' }))

    expect(await screen.findByRole('dialog', { name: '新建UI测试任务' })).toBeTruthy()
    await waitFor(() => expect(api.fetchScripts.mock.calls.length).toBeGreaterThan(0))
    await new Promise((resolve) => setTimeout(resolve, 0))
    // (batch-165) 页面新增「用例 / 脚本」页签，挂载时预加载脚本资产 1 次 + 选择器 1 次 = 2
    expect(api.fetchScripts).toHaveBeenCalledTimes(2)
  })

  it('截图通过受保护 API 加载为 Blob URL', async () => {
    api.fetchRunArtifactBlob.mockResolvedValue(new Blob(['evidence'], { type: 'image/png' }))

    render(
      <ProtectedArtifactMedia
        runId={42}
        path="screenshots/home.png"
        name="业务首页证据"
        kind="image"
      />,
    )

    const image = await screen.findByRole('img', { name: '业务首页证据' })
    expect(api.fetchRunArtifactBlob).toHaveBeenCalledWith(
      42,
      'screenshots/home.png',
      expect.any(AbortSignal),
    )
    expect(image.getAttribute('src')).toBe('blob:protected-artifact')
  })

  it('生产任务展示目标并在显式确认后提交 confirm_prod', async () => {
    useAuthStore.setState({
      permissions: ['uitest:list', 'uitest:trigger', 'uitest:trigger_prod'],
    })
    environmentApi.fetchEnvironments.mockResolvedValue([
      {
        id: 9,
        project_id: 1,
        name: '生产只读',
        env_type: 'prod',
        base_url: 'https://production.example.invalid',
        description: '',
        is_production: true,
        created_at: null,
        updated_at: null,
      },
    ])
    api.fetchUiJobs.mockResolvedValue({
      total: 1,
      page: 1,
      page_size: 20,
      items: [{
        id: 42,
        project_id: 1,
        name: '生产只读冒烟',
        description: '',
        test_spec: 'specs/production-smoke.spec.ts',
        browser: 'chromium',
        environment_id: 9,
        status: 'idle',
        last_result: '{}',
        creator_id: 1,
        created_at: null,
        updated_at: null,
      }],
    })

    render(<MemoryRouter><UiTestPage /></MemoryRouter>)

    expect(await screen.findByText('生产只读')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: '执行' }))

    expect(await screen.findByRole('alertdialog')).toBeTruthy()
    expect(screen.getByText('https://production.example.invalid')).toBeTruthy()
    expect(api.triggerUiJob).not.toHaveBeenCalled()

    fireEvent.click(screen.getByRole('button', { name: '确认执行生产任务' }))
    await waitFor(() => expect(api.triggerUiJob).toHaveBeenCalledWith(42, true))
  })

  it('缺少生产执行权限时禁用生产任务执行按钮', async () => {
    useAuthStore.setState({ permissions: ['uitest:list', 'uitest:trigger'] })
    environmentApi.fetchEnvironments.mockResolvedValue([
      {
        id: 9,
        project_id: 1,
        name: '生产只读',
        env_type: 'prod',
        base_url: 'https://production.example.invalid',
        description: '',
        is_production: true,
        created_at: null,
        updated_at: null,
      },
    ])
    api.fetchUiJobs.mockResolvedValue({
      total: 1,
      page: 1,
      page_size: 20,
      items: [{
        id: 42,
        project_id: 1,
        name: '生产只读冒烟',
        description: '',
        test_spec: 'specs/production-smoke.spec.ts',
        browser: 'chromium',
        environment_id: 9,
        status: 'idle',
        last_result: '{}',
        creator_id: 1,
        created_at: null,
        updated_at: null,
      }],
    })

    render(<MemoryRouter><UiTestPage /></MemoryRouter>)

    const trigger = await screen.findByRole('button', { name: '执行' })
    expect((trigger as HTMLButtonElement).disabled).toBe(true)
    expect(trigger.getAttribute('title')).toContain('uitest:trigger_prod')
  })
})
