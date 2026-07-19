import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const fetchTestCases = vi.fn()
const fetchEnvironments = vi.fn()
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
  fetchEnvironments: (...args: any[]) => fetchEnvironments(...args),
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
    fetchEnvironments.mockReset().mockResolvedValue([
      {
        id: 5,
        name: '测试5',
        env_type: 'test',
        base_url: 'http://camel-api-gateway05.svc.elelive.cn/',
      },
      {
        id: 6,
        name: '预发布',
        env_type: 'staging',
        base_url: 'https://staging.example.com',
      },
    ])
    executeApiCase.mockReset().mockResolvedValue({
      status: 'ok',
      status_code: 200,
      response_headers: {},
      response_body: { ok: true },
      duration_ms: 10,
      assertions: [],
      all_pass: true,
      vpn: {
        required: true,
        status: 'connected',
        connected_now: true,
        message: 'OpenVPN 已自动连接',
      },
    })
    createApiExecutionTask.mockReset().mockResolvedValue({ task_id: 'API-TEST', total: 1 })
  })

  it('默认使用测试5执行接口用例并提示自动连接 OpenVPN', async () => {
    render(<ApiCaseTab />)

    expect(screen.queryByText('响应结果')).toBeNull()
    expect(await screen.findByText('发送时自动连接 OpenVPN')).toBeTruthy()
    const environment = screen.getByRole('combobox', { name: '接口用例运行环境' })
    expect(environment.textContent).toContain('测试5')

    const interfaceTrigger = await screen.findByRole('button', { name: /接口C.*2 条用例/ })
    fireEvent.click(interfaceTrigger)
    fireEvent.click(await screen.findByText('C1'))

    await waitFor(() => expect(executeApiCase).toHaveBeenCalledWith(1, 5))
    expect(await screen.findByRole('dialog')).toBeTruthy()
    expect(screen.getByText(/接口响应/).textContent).toContain('正常请求')
    expect(await screen.findByText('OpenVPN 已自动连接')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'Close' }))

    fireEvent.click(screen.getByRole('button', { name: '选择接口 接口C 的全部用例' }))
    fireEvent.click(screen.getByRole('button', { name: '批量执行 (2)' }))
    await waitFor(() => expect(createApiExecutionTask).toHaveBeenCalledWith(expect.objectContaining({
      case_ids: [1, 2],
      environment_id: 5,
    })))
  })

  it('接口作为集合且默认收起，展开后显示该接口全部用例', async () => {
    render(<ApiCaseTab />)

    const interfaceTrigger = await screen.findByRole('button', { name: /接口C.*2 条用例/ })
    expect(screen.queryByText('【正向】接口C - 正常请求')).toBeNull()

    fireEvent.click(interfaceTrigger)
    expect(await screen.findByText('【正向】接口C - 正常请求')).toBeTruthy()
    expect(screen.getByText('【类型校验】接口C - age - 类型错误')).toBeTruthy()
  })
})
