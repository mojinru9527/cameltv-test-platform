import { beforeEach, describe, expect, it, vi } from 'vitest'

const { get } = vi.hoisted(() => ({ get: vi.fn() }))

vi.mock('../client', () => ({
  default: { get },
}))

import { fetchMenus } from '../auth'
import { fetchApiEndpoints, fetchApiServices } from '../apitest'
import { fetchUiJobs, fetchScripts } from '../uitest'
import { fetchAvTasks } from '../avcheck'
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
  })

  it('forwards AbortSignal through every Batch56 initial GET', async () => {
    const signal = new AbortController().signal

    await fetchMenus(signal)
    await fetchApiServices(signal)
    await fetchApiEndpoints({ page: 1 }, signal)
    await fetchUiJobs({ page: 1 }, signal)
    await fetchScripts(signal)
    await fetchAvTasks({ page: 1 }, signal)
    await fetchKnowledgeOverview(signal)
    await fetchAgentRuns({ page_size: 50 }, signal)
    await fetchAgentRun(7, signal)
    await fetchAgentTypes(signal)
    await fetchQueueItems({ page_size: 100 }, signal)
    await fetchQueueStats(signal)
    await fetchPlan(9, signal)
    await fetchExecutions(9, undefined, signal)

    expect(get.mock.calls).toEqual([
      ['/system/menus', { signal }],
      ['/apitest/services', { signal }],
      ['/apitest/endpoints', { params: { page: 1 }, signal }],
      ['/ui-tests', { params: { page: 1 }, signal }],
      ['/ui-tests/scripts', { signal }],
      ['/av-checks', { params: { page: 1 }, signal }],
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
