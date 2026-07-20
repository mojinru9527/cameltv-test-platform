import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const fetchTestCases = vi.fn()
const executeApiCase = vi.fn()
const createApiExecutionTask = vi.fn()

vi.mock('@/api/testcase', () => ({
  fetchTestCases: (...args: any[]) => fetchTestCases(...args),
}))
vi.mock('@/api/apitest', () => ({
  executeApiCase: (...args: any[]) => executeApiCase(...args),
  createApiExecutionTask: (...args: any[]) => createApiExecutionTask(...args),
  quickExecute: vi.fn(),
}))
vi.mock('@/api/environment', () => ({
  fetchEnvironments: (...args: any[]) => Promise.resolve([]),
}))
vi.mock('@/stores/auth', () => ({
  useAuthStore: (selector: (state: { currentProjectId: number }) => unknown) => selector({ currentProjectId: 1 }),
}))

import ApiCaseTab from './ApiCaseTab'

describe('接口用例列表', () => {
  beforeEach(() => {
    fetchTestCases.mockReset().mockResolvedValue({
      total: 2,
      items: [
        {
          id: 1,
          case_id: 'C1',
          title: '【正向】接口C - 正常请求',
          api_spec_ref: 'api_endpoint:9',
          api_method: 'POST',
          api_endpoint: '/api/c',
          priority: 'P0',
        },
        {
          id: 2,
          case_id: 'C2',
          title: '【类型校验】接口C - age - 类型错误',
          api_spec_ref: 'api_endpoint:9',
          api_method: 'POST',
          api_endpoint: '/api/c?age=bad',
          priority: 'P1',
        },
      ],
    })
    executeApiCase.mockReset().mockResolvedValue({
      status: 'ok',
      status_code: 200,
      response_headers: {},
      response_body: { ok: true },
      duration_ms: 10,
      assertions: [],
      all_pass: true,
    })
    createApiExecutionTask.mockReset().mockResolvedValue({ task_id: 'API-TEST', total: 1 })
  })

  it('接口用例按 endpoint 分组显示，点击用例执行并查看响应', async () => {
    render(<ApiCaseTab />)

    // Group shows endpoint path and method badge
    expect(await screen.findByText('/api/c')).toBeTruthy()
    expect(screen.getByText('POST')).toBeTruthy()

    // Cases hidden when group is collapsed
    expect(screen.queryByText('【正向】接口C - 正常请求')).toBeNull()

    // Expand group by clicking the collapsible trigger
    const endpointEl = screen.getByText('/api/c')
    const trigger = endpointEl.closest('button')
    if (trigger) fireEvent.click(trigger)

    // Case titles now visible
    const c1Title = await screen.findByText('【正向】接口C - 正常请求')
    expect(c1Title).toBeTruthy()
    expect(screen.getByText('【类型校验】接口C - age - 类型错误')).toBeTruthy()

    // Click case to execute
    fireEvent.click(c1Title)
    await waitFor(() => expect(executeApiCase).toHaveBeenCalledWith(1))

    // Response dialog opens
    expect(await screen.findByRole('dialog')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'Close' }))

    // Check batch execute
    fireEvent.click(screen.getByRole('button', { name: '全选' }))
    fireEvent.click(screen.getByRole('button', { name: /批量执行/ }))
    await waitFor(() => expect(createApiExecutionTask).toHaveBeenCalledWith(expect.objectContaining({
      case_ids: [1, 2],
    })))
  })
})
