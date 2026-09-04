import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const mocks = vi.hoisted(() => ({
  listOnboardings: vi.fn(),
  getOnboardingReadiness: vi.fn(),
  createOnboarding: vi.fn(),
  advanceOnboarding: vi.fn(),
  toastSuccess: vi.fn(),
  toastError: vi.fn(),
}))

vi.mock('@/api/versionTask', () => ({
  listOnboardings: (...args: unknown[]) => mocks.listOnboardings(...args),
  getOnboardingReadiness: (...args: unknown[]) => mocks.getOnboardingReadiness(...args),
  createOnboarding: (...args: unknown[]) => mocks.createOnboarding(...args),
  advanceOnboarding: (...args: unknown[]) => mocks.advanceOnboarding(...args),
}))

vi.mock('sonner', () => ({
  toast: { success: mocks.toastSuccess, error: mocks.toastError },
}))

const { default: OnboardingPage } = await import('@/pages/onboarding')

const readyState = {
  project_id: 1,
  checked_at: '2026-09-03T10:00:00Z',
  baseline_ready: true,
  durable_ready: false,
  services: {
    ai_provider: { status: 'ready', message: '最近一次真实调用成功', managed_by: 'project_admin' },
    temporal: { status: 'blocked', message: '耐久运行未启用', managed_by: 'platform' },
    runtime_worker: { status: 'blocked', message: '没有在线执行节点', managed_by: 'platform', online_count: 0 },
  },
}

function renderPage() {
  return render(<MemoryRouter><OnboardingPage /></MemoryRouter>)
}

describe('AI 全链路接入页', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mocks.listOnboardings.mockResolvedValue([])
    mocks.getOnboardingReadiness.mockResolvedValue(readyState)
  })

  it('明确展示六个用户必填字段，未填完不能开始', async () => {
    renderPage()
    await screen.findByText('平台自动检查')

    expect(screen.getByLabelText('业务名称')).toBeTruthy()
    expect(screen.getByLabelText('服务标识')).toBeTruthy()
    expect(screen.getByLabelText('本次版本')).toBeTruthy()
    expect(screen.getByLabelText('需求内容')).toBeTruthy()
    expect(screen.getByLabelText('OpenAPI 地址')).toBeTruthy()
    expect(screen.getByLabelText('被测服务地址')).toBeTruthy()
    expect((screen.getByRole('button', { name: '保存并开始接入' }) as HTMLButtonElement).disabled).toBe(true)
  })

  it('说明 Temporal 与 Worker 由平台常驻管理且区分两种就绪口径', async () => {
    renderPage()

    await screen.findByText('平台自动检查')
    expect(screen.getByText('业务接入基线已就绪')).toBeTruthy()
    expect(screen.getByText('可选耐久执行尚未就绪')).toBeTruthy()
    expect(screen.getByText(/不影响当前业务接入和同步基线/)).toBeTruthy()
    expect(screen.getAllByText('由平台常驻管理，无需每次手动启动')).toHaveLength(2)
    expect(mocks.getOnboardingReadiness).toHaveBeenCalledTimes(1)
    expect(mocks.listOnboardings).toHaveBeenCalledTimes(1)
  })

  it('填写完成后提交版本与需求正文', async () => {
    mocks.createOnboarding.mockResolvedValue({
      id: 3,
      name: '体育平台',
      service_key: 'sports-service',
      version: '16.0.0',
      requirement_text: '验证比分与文章链路',
      api_spec_url: 'https://sports.test/openapi.json',
      base_url: 'https://sports.test',
      status: 'onboarding',
      step: 1,
      version_task_id: null,
      baseline: '{}',
    })
    renderPage()
    await screen.findByText('平台自动检查')

    fireEvent.change(screen.getByLabelText('业务名称'), { target: { value: '体育平台' } })
    fireEvent.change(screen.getByLabelText('服务标识'), { target: { value: 'sports-service' } })
    fireEvent.change(screen.getByLabelText('本次版本'), { target: { value: '16.0.0' } })
    fireEvent.change(screen.getByLabelText('需求内容'), { target: { value: '验证比分与文章链路' } })
    fireEvent.change(screen.getByLabelText('OpenAPI 地址'), { target: { value: 'https://sports.test/openapi.json' } })
    fireEvent.change(screen.getByLabelText('被测服务地址'), { target: { value: 'https://sports.test' } })
    fireEvent.click(screen.getByRole('button', { name: '保存并开始接入' }))

    await waitFor(() => expect(mocks.createOnboarding).toHaveBeenCalledWith({
      name: '体育平台',
      service_key: 'sports-service',
      version: '16.0.0',
      requirement_text: '验证比分与文章链路',
      api_spec_url: 'https://sports.test/openapi.json',
      base_url: 'https://sports.test',
    }))
    expect(screen.getByText('查看已保存需求（9 字）')).toBeTruthy()
  })

  it('自动检查失败时提供原位重试', async () => {
    mocks.getOnboardingReadiness.mockRejectedValueOnce(new Error('检查服务暂不可用'))
    renderPage()

    await screen.findByText('自动检查失败')
    fireEvent.click(screen.getByRole('button', { name: '重新检查' }))

    await waitFor(() => expect(mocks.getOnboardingReadiness).toHaveBeenCalledTimes(2))
    expect(await screen.findByText('平台自动检查')).toBeTruthy()
  })
})
