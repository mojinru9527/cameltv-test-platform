import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

// Radix Select 在 jsdom 需要 scrollIntoView
if (!Element.prototype.scrollIntoView) {
  Element.prototype.scrollIntoView = () => undefined
}

// jest-dom 未安装 → 提供语义对齐的最小 matcher
expect.extend({
  toBeInTheDocument(received: Element | null) {
    const pass = received !== null && document.documentElement.contains(received)
    return { pass, message: () => (pass ? 'element is in the document' : 'element is not in the document') }
  },
})

const mocks = vi.hoisted(() => ({
  createDshTask: vi.fn(),
  toastSuccess: vi.fn(),
  toastError: vi.fn(),
}))

vi.mock('@/api/dshTasks', () => ({
  createDshTask: (...args: unknown[]) => mocks.createDshTask(...args),
}))
vi.mock('@/api/aiConfig', () => ({}))
vi.mock('sonner', () => ({
  toast: { success: mocks.toastSuccess, error: mocks.toastError },
}))

const { default: SceneWizard } = await import('../SceneWizard')
const { SCENES } = await import('../../scenes')

const functional = SCENES.find((s) => s.id === 'functional')!

const providers = [
  {
    id: 1,
    name: 'DeepSeek 生产',
    provider_type: 'deepseek_official',
    api_base_url: 'https://api.deepseek.com',
    api_key: 'sk****cdef',
    models: ['deepseek-v4-pro', 'deepseek-v4-flash'],
    default_model: 'deepseek-v4-pro',
    is_default: true,
    enabled: true,
  },
]

function renderWizard(open = true, _providers: typeof providers = providers) {
  return render(
    <MemoryRouter>
      <SceneWizard
        open={open}
        onOpenChange={() => {}}
        scene={functional}
        providers={_providers}
        onSubmitted={() => {}}
      />
    </MemoryRouter>,
  )
}

describe('SceneWizard 三步向导', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    cleanup()
  })

  it('打开后显示输入区，空输入时"下一步"禁用', () => {
    renderWizard()
    expect(screen.getByLabelText(functional.inputLabel)).toBeInTheDocument()
    const nextBtn = screen.getByRole('button', { name: '下一步' })
    expect(nextBtn).toBeTruthy()
    expect((nextBtn as HTMLButtonElement).disabled).toBe(true)
  })

  it('输入 → 下一步 → 无 providers 显示未配置提示且"下一步"禁用', async () => {
    renderWizard(true, [])
    fireEvent.change(screen.getByLabelText(functional.inputLabel), { target: { value: '测试需求文本' } })
    fireEvent.click(screen.getByRole('button', { name: '下一步' }))

    await waitFor(() => expect(screen.getByText(/当前项目未配置 AI 提供方/)).toBeInTheDocument())
    expect(screen.getByRole('button', { name: '下一步' })).toBeTruthy()
    expect((screen.getByRole('button', { name: '下一步' }) as HTMLButtonElement).disabled).toBe(true)
  })

  it('输入 + providers → 走完三步 → 提交 → createDshTask 被调', async () => {
    mocks.createDshTask.mockResolvedValue({ id: 1 })
    renderWizard()

    // Step 1
    fireEvent.change(screen.getByLabelText(functional.inputLabel), { target: { value: '功能需求内容' } })
    fireEvent.click(screen.getByRole('button', { name: '下一步' }))

    // Step 2（配置）
    await waitFor(() => expect(screen.getByText('AI 提供方')).toBeInTheDocument())
    fireEvent.click(screen.getByRole('button', { name: '下一步' }))

    // Step 3
    await waitFor(() => expect(screen.getByText('任务描述（可编辑）')).toBeInTheDocument())
    const taskTextarea = screen.getByLabelText('任务描述（可编辑）') as HTMLTextAreaElement
    expect(taskTextarea.value).toContain('功能需求内容')

    fireEvent.click(screen.getByRole('button', { name: '提交' }))

    await waitFor(() => expect(mocks.createDshTask).toHaveBeenCalledTimes(1))
    const args = mocks.createDshTask.mock.calls[0]
    expect(args[3]).toBe('functional')
    expect(args[0]).toContain('功能需求内容')
    const params = args[1] as Record<string, any>
    expect(params.model).toBe('deepseek-v4-pro')
    expect(params.batch_mode).toBe('full')
    expect(mocks.toastSuccess).toHaveBeenCalledWith('DSH 任务已提交')
  })

  it('提交失败 → toast.error 被调', async () => {
    mocks.createDshTask.mockRejectedValue(new Error('提交失败'))
    renderWizard()

    fireEvent.change(screen.getByLabelText(functional.inputLabel), { target: { value: '功能需求内容' } })
    fireEvent.click(screen.getByRole('button', { name: '下一步' }))
    await waitFor(() => expect(screen.getByText('AI 提供方')).toBeInTheDocument())
    fireEvent.click(screen.getByRole('button', { name: '下一步' }))
    await waitFor(() => expect(screen.getByText('任务描述（可编辑）')).toBeInTheDocument())

    fireEvent.click(screen.getByRole('button', { name: '提交' }))

    await waitFor(() => expect(mocks.toastError).toHaveBeenCalledWith('提交失败'))
  })
})
