import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

// 仓库未安装 @testing-library/jest-dom，提供语义对齐的最小 matcher
expect.extend({
  toBeInTheDocument(received: Element | null) {
    const pass = received !== null && document.documentElement.contains(received)
    return { pass, message: () => (pass ? 'element is in the document' : 'element is not in the document') }
  },
})

const mocks = vi.hoisted(() => ({
  canManage: true,
  fetchAiProviders: vi.fn(),
  createAiProvider: vi.fn(),
  updateAiProvider: vi.fn(),
  deleteAiProvider: vi.fn(),
  testAiProviderConnection: vi.fn(),
  fetchAiResolve: vi.fn(),
  discoverAiModels: vi.fn(),
  toastSuccess: vi.fn(),
  toastError: vi.fn(),
}))

vi.mock('@/stores/auth', () => ({
  useAuthStore: (selector: (state: { hasPerm: (permission: string) => boolean }) => unknown) =>
    selector({ hasPerm: (permission) => permission !== 'ai_config:manage' || mocks.canManage }),
}))

vi.mock('@/api/aiConfig', () => ({
  fetchAiProviders: (...args: unknown[]) => mocks.fetchAiProviders(...args),
  createAiProvider: (...args: unknown[]) => mocks.createAiProvider(...args),
  updateAiProvider: (...args: unknown[]) => mocks.updateAiProvider(...args),
  deleteAiProvider: (...args: unknown[]) => mocks.deleteAiProvider(...args),
  testAiProviderConnection: (...args: unknown[]) => mocks.testAiProviderConnection(...args),
  fetchAiResolve: (...args: unknown[]) => mocks.fetchAiResolve(...args),
  discoverAiModels: (...args: unknown[]) => mocks.discoverAiModels(...args),
}))

vi.mock('sonner', () => ({
  toast: { success: mocks.toastSuccess, error: mocks.toastError },
}))

const { default: AiConfigPage } = await import('@/pages/ai-config')

// name 故意与类型 label（"DeepSeek 官方"）不同，避免 getByText 歧义
const provider = {
  id: 1,
  name: 'DeepSeek 生产',
  provider_type: 'deepseek_official',
  api_base_url: 'https://api.deepseek.com',
  api_key: 'sk****cdef',
  models: ['deepseek-v4-pro', 'deepseek-v4-flash'],
  default_model: 'deepseek-v4-pro',
  is_default: true,
  enabled: true,
}

describe('AI 配置页', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mocks.canManage = true
    mocks.fetchAiProviders.mockResolvedValue([])
    mocks.fetchAiResolve.mockResolvedValue({ configured: false, provider: null })
    mocks.discoverAiModels.mockResolvedValue({ ok: true, models: [], count: 0 })
  })

  /** 自动发现按钮在新建/编辑抽屉内部，必须先打开抽屉。 */
  async function openCreateDrawer() {
    render(<AiConfigPage />)
    await waitFor(() =>
      expect(screen.getByText(/当前项目未配置 AI 提供方/)).toBeInTheDocument(),
    )
    fireEvent.click(screen.getByRole('button', { name: /新建提供方/ }))
    await waitFor(() => expect(screen.getByLabelText('API 地址')).toBeInTheDocument())
  }

  it('空列表显示未配置引导', async () => {
    render(<AiConfigPage />)
    await waitFor(() =>
      expect(screen.getByText(/当前项目未配置 AI 提供方/)).toBeInTheDocument(),
    )
  })

  it('有数据时渲染列表并显示掩码 key', async () => {
    mocks.fetchAiProviders.mockResolvedValue([provider])
    render(<AiConfigPage />)
    await waitFor(() => expect(screen.getByText('DeepSeek 生产')).toBeInTheDocument())
    expect(screen.getByText('sk****cdef')).toBeInTheDocument()
    expect(screen.getByText('deepseek-v4-pro')).toBeInTheDocument()
  })

  it('无 ai_config:manage 权限时不显示新建按钮与编辑/删除', async () => {
    mocks.canManage = false
    mocks.fetchAiProviders.mockResolvedValue([provider])
    render(<AiConfigPage />)
    await waitFor(() => expect(screen.getByText('DeepSeek 生产')).toBeInTheDocument())
    expect(screen.queryByRole('button', { name: /新建提供方/ })).not.toBeInTheDocument()
    expect(screen.queryByTitle('编辑')).not.toBeInTheDocument()
    expect(screen.queryByTitle('删除')).not.toBeInTheDocument()
  })

  it('测试连接成功时提示连通正常', async () => {
    mocks.fetchAiProviders.mockResolvedValue([provider])
    mocks.testAiProviderConnection.mockResolvedValue({ ok: true, latency_ms: 320, model: 'deepseek-v4-pro' })
    render(<AiConfigPage />)
    await waitFor(() => expect(screen.getByText('DeepSeek 生产')).toBeInTheDocument())
    fireEvent.click(screen.getByTitle('测试连通性'))
    await waitFor(() => expect(mocks.toastSuccess).toHaveBeenCalled())
  })

  // ── Batch 230 S4 / DEF-20260905-004 ──
  // 表单已填模型时，发现失败仍会与既有模型合并出非空清单，旧代码据此弹绿色成功提示。
  it('自动发现返回 ok=false 时报错且不合并既有清单', async () => {
    mocks.discoverAiModels.mockResolvedValue({
      ok: false,
      kind: 'unauthorized',
      error: 'API Key 无效或已过期',
    })
    await openCreateDrawer()
    fireEvent.change(screen.getByLabelText('API 地址'), {
      target: { value: 'https://api.deepseek.com' },
    })
    fireEvent.change(screen.getByLabelText('模型清单（逗号分隔）'), {
      target: { value: 'deepseek-v4-pro, deepseek-chat' },
    })

    fireEvent.click(screen.getByRole('button', { name: /自动发现/ }))

    // 精确匹配调用参数：发现失败发生在未保存的表单内，不得给「更新密钥」action（会嵌套打开抽屉）。
    await waitFor(() =>
      expect(mocks.toastError).toHaveBeenCalledWith('API Key 无效或已过期', { duration: 10_000 }),
    )
    expect(mocks.toastSuccess).not.toHaveBeenCalled()
    expect((screen.getByLabelText('模型清单（逗号分隔）') as HTMLInputElement).value).toBe(
      'deepseek-v4-pro, deepseek-chat',
    )
  })

  it('自动发现成功时用后端 count 报数并合并既有模型', async () => {
    mocks.discoverAiModels.mockResolvedValue({ ok: true, models: ['m1', 'm2'], count: 2 })
    await openCreateDrawer()
    fireEvent.change(screen.getByLabelText('API 地址'), {
      target: { value: 'https://api.deepseek.com' },
    })
    fireEvent.change(screen.getByLabelText('模型清单（逗号分隔）'), {
      target: { value: 'existing' },
    })

    fireEvent.click(screen.getByRole('button', { name: /自动发现/ }))

    await waitFor(() =>
      expect(mocks.toastSuccess).toHaveBeenCalledWith('已拉取 2 个模型，合并后共 3 个'),
    )
    expect(mocks.toastError).not.toHaveBeenCalled()
    expect((screen.getByLabelText('模型清单（逗号分隔）') as HTMLInputElement).value).toBe(
      'existing, m1, m2',
    )
  })
})
