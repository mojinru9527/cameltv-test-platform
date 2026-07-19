import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const fetchApiServices = vi.fn()
const fetchApiEndpoints = vi.fn()

vi.mock('@/api/apitest', () => ({
  fetchApiServices: (...args: any[]) => fetchApiServices(...args),
  fetchApiEndpoints: (...args: any[]) => fetchApiEndpoints(...args),
  generateApiCases: vi.fn(),
}))

import AssetTab from './AssetTab'

const services = [
  {
    id: 1,
    project_id: 1,
    name: 'service-a',
    display_name: '服务 A',
    description: '',
    default_base_path: '',
    owner: '',
    status: 'active',
    endpoint_count: 1,
    created_at: null,
    updated_at: null,
  },
  {
    id: 2,
    project_id: 1,
    name: 'service-b',
    display_name: '服务 B',
    description: '',
    default_base_path: '',
    owner: '',
    status: 'active',
    endpoint_count: 1,
    created_at: null,
    updated_at: null,
  },
]

function endpoint(id: number, serviceId: number, module: string, path: string) {
  return {
    id,
    project_id: 1,
    service_id: serviceId,
    module,
    method: 'GET',
    path,
    summary: `${module} 接口`,
    description: '',
    request_schema: '{}',
    response_schema: '{}',
    auth_required: false,
    deprecated: false,
    source: 'openapi',
    import_batch_id: 1,
    version: '1.0',
    created_at: null,
    updated_at: null,
  }
}

describe('接口资产服务与模块层级', () => {
  beforeEach(() => {
    fetchApiServices.mockReset().mockResolvedValue(services)
    fetchApiEndpoints.mockReset().mockImplementation(({ service_id }: { service_id?: number }) => {
      const items = service_id === 2
        ? [endpoint(2, 2, '/orders', '/list')]
        : [endpoint(1, 1, '/users', '/list')]
      return Promise.resolve({ items, total: items.length, page: 1, page_size: 100 })
    })
  })

  it('以服务为 Tab，且每个服务下的模块默认收起', async () => {
    render(<AssetTab onOpenImport={vi.fn()} refreshKey={0} />)

    expect(await screen.findByRole('tab', { name: /服务 A/ })).toBeTruthy()
    expect(screen.getByRole('tab', { name: /服务 B/ })).toBeTruthy()

    const usersModule = await screen.findByRole('button', { name: /users/ })
    expect(screen.queryByText('/list')).toBeNull()
    fireEvent.click(usersModule)
    expect(await screen.findByText('/list')).toBeTruthy()

    const serviceBTab = screen.getByRole('tab', { name: /服务 B/ })
    fireEvent.mouseDown(serviceBTab, { button: 0, ctrlKey: false })
    await waitFor(() => expect(fetchApiEndpoints).toHaveBeenLastCalledWith(expect.objectContaining({ service_id: 2 })))
    expect(await screen.findByRole('button', { name: /orders/ })).toBeTruthy()
    expect(screen.queryByText('/list')).toBeNull()
  })

  it('服务 Tab 提供左右滑动控制并按可滚动范围禁用', async () => {
    render(<AssetTab onOpenImport={vi.fn()} refreshKey={0} />)

    await screen.findByRole('tab', { name: /服务 A/ })
    const viewport = screen.getByTestId('service-tabs-viewport')
    Object.defineProperties(viewport, {
      clientWidth: { configurable: true, value: 200 },
      scrollWidth: { configurable: true, value: 600 },
      scrollLeft: { configurable: true, writable: true, value: 0 },
    })
    const scrollBy = vi.fn()
    Object.defineProperty(viewport, 'scrollBy', { configurable: true, value: scrollBy })
    fireEvent.scroll(viewport)

    const previous = screen.getByRole('button', { name: '向左查看更多服务' })
    const next = screen.getByRole('button', { name: '向右查看更多服务' })
    await waitFor(() => expect((next as HTMLButtonElement).disabled).toBe(false))
    expect((previous as HTMLButtonElement).disabled).toBe(true)

    fireEvent.click(next)
    expect(scrollBy).toHaveBeenCalledWith(expect.objectContaining({ left: 240, behavior: 'smooth' }))

    Object.defineProperty(viewport, 'scrollLeft', { configurable: true, value: 400 })
    fireEvent.scroll(viewport)
    await waitFor(() => expect((previous as HTMLButtonElement).disabled).toBe(false))
    expect((next as HTMLButtonElement).disabled).toBe(true)
  })
})
