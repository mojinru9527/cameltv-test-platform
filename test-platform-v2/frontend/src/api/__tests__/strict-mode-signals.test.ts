import { beforeEach, describe, expect, it, vi } from 'vitest'

const { get, cachedGetMock } = vi.hoisted(() => ({
  get: vi.fn(),
  cachedGetMock: vi.fn(),
}))

vi.mock('../client', () => ({
  default: { get },
  cachedGet: cachedGetMock,
  clearApiCache: vi.fn(),
}))

import { fetchMenus } from '../auth'
import { fetchApiEndpoints, fetchApiServices } from '../apitest'
import { fetchUiJobs, fetchScripts } from '../uitest'
import { fetchKnowledgeOverview } from '../knowledge'
// (P1b) api/agent.ts 已随 Agent 工作台页面删除（入口收敛进 DSH 任务）；
// 后端 /agents API 保留，其 signal 透传契约不再由前端覆盖。
import { fetchExecutions, fetchPlan } from '../testplan'

describe('StrictMode request cancellation contracts', () => {
  beforeEach(() => {
    get.mockReset().mockResolvedValue({})
    cachedGetMock.mockReset().mockResolvedValue({})
  })

  it('forwards AbortSignal through every Batch56 initial GET', async () => {
    const signal = new AbortController().signal

    await fetchMenus(signal)
    await fetchApiServices(signal)
    await fetchApiEndpoints({ page: 1 }, signal)
    await fetchUiJobs({ page: 1 }, signal)
    await fetchScripts(signal)
    await fetchKnowledgeOverview(signal)
    await fetchPlan(9, signal)
    await fetchExecutions(9, undefined, signal)

    // Batch 176（FIX-173-P1-02）：fetchMenus 走 cachedGet 并透传 signal；
    // 其余 API 仍直连 client.get 转发 signal。
    expect(cachedGetMock).toHaveBeenCalledWith(
      '/system/menus', undefined,
      expect.objectContaining({ signal }),
    )
    expect(get.mock.calls).toEqual([
      ['/apitest/services', { signal }],
      ['/apitest/endpoints', { params: { page: 1 }, signal }],
      ['/ui-tests', { params: { page: 1 }, signal }],
      ['/ui-tests/scripts', { signal }],
      ['/knowledge/overview', { signal }],
      ['/test-plans/9', { signal }],
      ['/test-plans/9/executions', { params: { pcase_id: 0 }, signal }],
    ])
  })
})
