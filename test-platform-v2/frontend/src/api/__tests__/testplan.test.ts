import { beforeEach, describe, expect, it, vi } from 'vitest'

const mockPost = vi.fn()

vi.mock('@/api/client', () => ({
  default: {
    post: (...args: unknown[]) => mockPost(...args),
  },
}))

const { triagePlanFailures } = await import('@/api/testplan')

describe('test plan triage API', () => {
  beforeEach(() => vi.clearAllMocks())

  // P1-7 契约：后端 /triage 的 use_llm 默认是 false（规则引擎），LLM 深度分析必须由
  // 调用方显式 opt-in。前端「开始分诊」是一次明确的用户动作，因此必须带上
  // use_llm=true —— 一旦这个参数被删掉，界面会静默退化成规则分诊而没有任何报错。
  it('triage 显式携带 use_llm=true（后端默认 false，必须 opt-in）', async () => {
    mockPost.mockResolvedValue({ plan_id: 7, total_failures: 0, classified: [], summary: {}, analysis_method: 'llm' })

    await triagePlanFailures(7)

    expect(mockPost).toHaveBeenCalledWith(
      '/test-plans/7/triage',
      null,
      { params: { use_llm: true } },
    )
  })
})
