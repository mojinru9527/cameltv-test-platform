import { beforeEach, describe, expect, it, vi } from 'vitest'

const { get, post, put } = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
  put: vi.fn(),
}))

vi.mock('../client', () => ({
  default: { get, post, put },
}))

import {
  fetchApiServices,
  fetchApiEndpoints,
  previewOpenApiImport,
  confirmOpenApiImport,
  generateApiCases,
  fetchApiExecutionTasks,
} from '../apitest'

describe('API 测试接口客户端', () => {
  beforeEach(() => {
    get.mockReset()
    post.mockReset()
    put.mockReset()
  })

  it('直接返回响应拦截器已经解包的服务和接口数据', async () => {
    const services = [{ id: 1, name: 'account-service' }]
    const endpoints = { total: 1, page: 1, page_size: 20, items: [{ id: 2, method: 'GET', path: '/users' }] }
    get.mockResolvedValueOnce(services).mockResolvedValueOnce(endpoints)

    await expect(fetchApiServices()).resolves.toEqual(services)
    await expect(fetchApiEndpoints({ page: 1 })).resolves.toEqual(endpoints)
  })

  it('直接返回预览、确认和用例生成结果', async () => {
    const preview = { version: '3.0.1', total_count: 2, new_count: 2, existing_count: 0, endpoints: [] }
    const imported = { service_id: 1, imported_count: 2, generated_case_count: 4 }
    const generated = { cases: [], total: 4, imported_case_ids: [1, 2, 3, 4] }
    post.mockResolvedValueOnce(preview).mockResolvedValueOnce(imported).mockResolvedValueOnce(generated)

    await expect(previewOpenApiImport({ service_name: 'camel-service', source_type: 'openapi_text' })).resolves.toEqual(preview)
    await expect(confirmOpenApiImport({ service_name: 'camel-service', source_type: 'openapi_text' })).resolves.toEqual(imported)
    await expect(generateApiCases({ endpoint_id: 1, templates: ['basic'], import_to_case_library: true })).resolves.toEqual(generated)
  })

  it('直接返回执行任务分页结果', async () => {
    const page = { total: 0, page: 1, page_size: 20, items: [] }
    get.mockResolvedValue(page)
    await expect(fetchApiExecutionTasks({ page: 1 })).resolves.toEqual(page)
  })
})
