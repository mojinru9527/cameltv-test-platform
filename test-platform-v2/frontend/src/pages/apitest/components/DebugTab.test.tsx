import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useAuthStore } from '@/stores/auth'

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
  async function selectTest5Environment() {
    fireEvent.click(await screen.findByLabelText('选择调试环境'))
    fireEvent.click(await screen.findByRole('option', { name: /测试5/ }))
  }

  beforeEach(() => {
    useAuthStore.setState({ permissions: ['*'], currentProjectId: 1 })
    Element.prototype.scrollIntoView = vi.fn()
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

    await selectTest5Environment()
    await screen.findByText('发送时自动连接 OpenVPN')
    fireEvent.change(screen.getByLabelText('接口路径'), { target: { value: '/health' } })
    fireEvent.click(screen.getByRole('button', { name: '发送' }))
    fireEvent.click(await screen.findByRole('button', { name: '确认执行测试操作' }))

    await waitFor(() => expect(quickExecute).toHaveBeenCalledWith(expect.objectContaining({
      source: 'quick',
      environment_id: 5,
    })))
    expect((await screen.findAllByText(/OpenVPN 自动连接失败/)).length).toBeGreaterThan(0)
  })

  it('直接进入快速调试时保持空 URL 和空请求参数', async () => {
    render(<DebugTab endpoint={null} />)

    await waitFor(() => expect(fetchEnvironments).toHaveBeenCalled())
    expect((screen.getByLabelText('服务器地址') as HTMLInputElement).value).toBe('')
    expect((screen.getByLabelText('服务名') as HTMLInputElement).value).toBe('')
    expect((screen.getByLabelText('模块名') as HTMLInputElement).value).toBe('')
    expect((screen.getByLabelText('接口路径') as HTMLInputElement).value).toBe('')
    expect(screen.queryByLabelText('参数 1 名称')).toBeNull()
    await waitFor(() => expect(fetchEnvironments).toHaveBeenCalled())
    expect(screen.queryByText('发送时自动连接 OpenVPN')).toBeNull()
    expect(screen.getByTestId('quick-debug-layout').className).not.toContain('grid-cols')
    expect(screen.getByTestId('quick-debug-response')).toBeTruthy()
  })

  it('为参数和 Header 的图标操作提供明确名称', async () => {
    render(<DebugTab endpoint={null} />)

    await waitFor(() => expect(fetchEnvironments).toHaveBeenCalled())

    const addParam = screen.getByRole('button', { name: '添加查询参数' })
    expect(addParam.getAttribute('aria-label')).toBe('添加查询参数')
    fireEvent.click(addParam)
    expect(screen.getByRole('button', { name: '删除查询参数 1' })).toBeTruthy()

    const addHeader = screen.getByRole('button', { name: '添加请求 Header' })
    expect(addHeader.getAttribute('aria-label')).toBe('添加请求 Header')
    fireEvent.click(addHeader)
    expect(screen.getByRole('button', { name: '删除请求 Header 1' })).toBeTruthy()
    expect(screen.getByRole('button', { name: '删除请求 Header 2' })).toBeTruthy()
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

    await selectTest5Environment()
    expect((screen.getByLabelText('服务器地址') as HTMLInputElement).value).toBe(
      'http://camel-api-gateway05.svc.elelive.cn/',
    )
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

  it('A组：tags 当模块时 URL 不再拼接模块名；参数取契约 example；默认断言非空', async () => {
    render(
      <DebugTab
        endpoint={{
          id: 2,
          project_id: 1,
          service_id: 3,
          service_name: 'camel-test-confirm',
          module: 'sports-live-controller',
          method: 'GET',
          path: '/ee/sports_live/home_match',
          summary: '首页赛事',
          description: '',
          request_schema: JSON.stringify({
            query: [{ name: 'day', type: 'string', required: true, example: '20260615' }],
            body: {
              content_type: 'application/json',
              properties: { formKey: { type: 'string', example: 'sport_live_follow_conf' } },
            },
          }),
          response_schema: '{}',
          auth_required: false,
          deprecated: false,
          source: 'knife4j',
          import_batch_id: 1,
          version: '1.0',
          created_at: null,
          updated_at: null,
        }}
      />,
    )

    await selectTest5Environment()
    // tags=sports-live-controller 不再作为模块路径混入
    expect((screen.getByLabelText('模块名') as HTMLInputElement).value).toBe('/ee/sports_live')
    expect((screen.getByLabelText('接口路径') as HTMLInputElement).value).toBe('/home_match')
    expect((screen.getByLabelText('完整请求地址') as HTMLInputElement).value).toBe(
      'http://camel-api-gateway05.svc.elelive.cn/camel-test-confirm/ee/sports_live/home_match',
    )
    // 参数预填取契约真实 example（不再空值/占位）
    expect((screen.getByLabelText('参数 1 名称') as HTMLInputElement).value).toBe('day')
    expect((screen.getByLabelText('参数 1 值') as HTMLInputElement).value).toBe('20260615')
    // 默认断言非空（2xx + 响应时间）
    expect(screen.getByText('断言规则 (3)')).toBeTruthy()
  })
})
