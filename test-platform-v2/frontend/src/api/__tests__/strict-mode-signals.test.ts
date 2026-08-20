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
import {
  fetchAgentRun,
  fetchAgentRuns,
  fetchAgentTypes,
  fetchQueueItems,
  fetchQueueStats,
} from '../agent'
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
    await fetchAgentRuns({ page_size: 50 }, signal)
    await fetchAgentRun(7, signal)
    await fetchAgentTypes(signal)
    await fetchQueueItems({ page_size: 100 }, signal)
    await fetchQueueStats(signal)
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
      ['/agents/runs', { params: { page_size: 50 }, signal }],
      ['/agents/runs/7', { signal }],
      ['/agents/types', { signal }],
      ['/agents/queue', { params: { page_size: 100 }, signal }],
      ['/agents/queue/stats', { signal }],
      ['/test-plans/9', { signal }],
      ['/test-plans/9/executions', { params: { pcase_id: 0 }, signal }],
    ])
  })
})
