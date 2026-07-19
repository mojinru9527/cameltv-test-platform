import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const fetchEnvironments = vi.fn()
const fetchDatasets = vi.fn()
const quickExecute = vi.fn()

vi.mock('@/api/apitest', () => ({
  quickExecute: (...args: any[]) => quickExecute(...args),
}))
vi.mock('@/api/environment', () => ({
  fetchEnvironments: (...args: any[]) => fetchEnvironments(...args),
}))
vi.mock('@/api/dataset', () => ({
  fetchDatasets: (...args: any[]) => fetchDatasets(...args),
}))

import DebugTab from './DebugTab'

describe('快速调试资产预填', () => {
  beforeEach(() => {
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
    fetchDatasets.mockReset().mockResolvedValue({ items: [] })
    quickExecute.mockReset()
  })

  it('OpenVPN 连接失败时在响应区显示原因且保留测试5环境', async () => {
    quickExecute.mockResolvedValueOnce({
      status: 'error',
      status_code: 0,
      response_headers: {},
      response_body: null,
      duration_ms: 0,
      assertions: [],
      all_pass: false,
      error: 'OpenVPN 自动连接失败，测试环境仍不可访问。',
      vpn: {
        required: true,
        status: 'error',
        connected_now: false,
        message: 'OpenVPN 自动连接失败，测试环境仍不可访问。',
      },
    })
    render(<DebugTab endpoint={null} />)

    await screen.findByText('发送时自动连接 OpenVPN')
    fireEvent.change(screen.getByLabelText('接口路径'), { target: { value: '/health' } })
    fireEvent.click(screen.getByRole('button', { name: '发送' }))

    await waitFor(() => expect(quickExecute).toHaveBeenCalledWith(expect.objectContaining({
      environment_id: 5,
    })))
    expect((await screen.findAllByText(/OpenVPN 自动连接失败/)).length).toBeGreaterThan(0)
  })

  it('直接进入快速调试时保持空 URL 和空请求参数', async () => {
    render(<DebugTab endpoint={null} />)

    expect((screen.getByLabelText('服务器地址') as HTMLInputElement).value).toBe(
      'http://camel-api-gateway05.svc.elelive.cn/',
    )
    expect((screen.getByLabelText('服务名') as HTMLInputElement).value).toBe('')
    expect((screen.getByLabelText('模块名') as HTMLInputElement).value).toBe('')
    expect((screen.getByLabelText('接口路径') as HTMLInputElement).value).toBe('')
    expect(screen.queryByLabelText('参数 1 名称')).toBeNull()
    await waitFor(() => expect(fetchEnvironments).toHaveBeenCalled())
    expect(await screen.findByText('发送时自动连接 OpenVPN')).toBeTruthy()
    expect(screen.getByTestId('quick-debug-layout').className).not.toContain('grid-cols')
    expect(screen.getByTestId('quick-debug-response')).toBeTruthy()
  })

  it('从接口资产进入时默认使用测试5并带入完整 URL 和参数格式', async () => {
    render(
      <DebugTab
        endpoint={{
          id: 1,
          project_id: 1,
          service_id: 2,
          service_name: 'camel-service',
          module: '',
          method: 'POST',
          path: '/ee/search/synonyms/cou',
          summary: '同义词查询',
          description: '',
          request_schema: JSON.stringify({
            query: [{ name: 'keyword', type: 'string', required: true }],
            path: [{ name: 'tenantId', type: 'string', required: true }],
            header: [{ name: 'X-Trace-Id', type: 'string', required: false }],
            body: {
              content_type: 'application/json',
              properties: { text: { type: 'string' } },
            },
          }),
          response_schema: '{}',
          auth_required: false,
          deprecated: false,
          source: 'openapi',
          import_batch_id: 1,
          version: '2.0',
          created_at: null,
          updated_at: null,
        }}
      />,
    )

    await waitFor(() => {
      expect((screen.getByLabelText('服务器地址') as HTMLInputElement).value).toBe(
        'http://camel-api-gateway05.svc.elelive.cn/',
      )
    })
    expect((screen.getByLabelText('服务名') as HTMLInputElement).value).toBe('camel-service')
    expect((screen.getByLabelText('模块名') as HTMLInputElement).value).toBe('/ee/search')
    expect((screen.getByLabelText('接口路径') as HTMLInputElement).value).toBe('/synonyms/cou')
    expect((screen.getByLabelText('完整请求地址') as HTMLInputElement).value).toBe(
      'http://camel-api-gateway05.svc.elelive.cn/camel-service/ee/search/synonyms/cou',
    )
    expect((screen.getByLabelText('参数 1 名称') as HTMLInputElement).value).toBe('tenantId')
    expect((screen.getByLabelText('参数 2 名称') as HTMLInputElement).value).toBe('keyword')
    expect((screen.getByLabelText('Header 2 名称') as HTMLInputElement).value).toBe('X-Trace-Id')
    expect((screen.getByLabelText('请求 Body') as HTMLTextAreaElement).value).toContain('"text"')
  })
})
