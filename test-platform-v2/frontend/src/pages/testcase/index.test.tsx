import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useAuthStore } from '@/stores/auth'

const api = vi.hoisted(() => ({
  batchDeleteCases: vi.fn(),
}))

vi.mock('sonner', () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}))

vi.mock('@/api/testcase', () => ({
  batchDeleteCases: (...args: unknown[]) => api.batchDeleteCases(...args),
  batchUpdateCases: vi.fn(),
  deleteTestCase: vi.fn(),
  fetchDomains: vi.fn(),
  fetchTestCases: vi.fn(),
  fetchTaxonomy: vi.fn(),
  fetchTestCaseStats: vi.fn(),
  fetchVersions: vi.fn(),
  reviewCase: vi.fn(),
}))

vi.mock('@/hooks/useApi', () => ({
  useApi: (_fetcher: unknown, deps: unknown[]) => {
    if (deps.length === 1) {
      return {
        data: [{
          surface: '用户端',
          count: 47,
          domains: [{
            domain: 'FAQ帮助',
            count: 27,
            modules: [
              { name: 'faq内容', path: 'faq内容', count: 5, children: [] },
              { name: '帮助中心', path: '帮助中心', count: 2, children: [] },
              { name: '异常恢复', path: '异常恢复', count: 1, children: [] },
              { name: '重复与并发', path: '重复与并发', count: 1, children: [] },
            ],
          }, {
            domain: '赛事详情',
            count: 20,
            modules: [{
              name: '订单列表',
              path: '赛事详情/订单列表',
              count: 12,
              children: [
                { name: '取消订单', path: '赛事详情/订单列表/取消订单', count: 4, children: [] },
                { name: '退款', path: '赛事详情/订单列表/退款', count: 3, children: [] },
              ],
            }, {
              name: '售后',
              path: '赛事详情/售后',
              count: 5,
              children: [],
            }],
          }],
        }],
        isLoading: false,
        isError: false,
        error: null,
        refetch: vi.fn(),
      }
    }
    if (deps.length === 0) {
      return { data: [], isLoading: false, isError: false, error: null, refetch: vi.fn() }
    }
    return {
        data: {
          total: 2,
          page: 1,
          page_size: 20,
          items: [
            { id: 11, title: '体育接口用例 A', domain: '赛事', module: '直播', priority: 'P0', positive_negative: 'positive', review_status: 'draft' },
            { id: 12, title: '体育接口用例 B', domain: '赛事', module: '直播', priority: 'P1', positive_negative: 'negative', review_status: 'draft' },
          ],
        },
        isLoading: false,
        isError: false,
        error: null,
        refetch: vi.fn(),
      }
  },
}))

vi.mock('@/components/DomainTree', () => ({
  default: ({ treeData }: { treeData: any[] }) => {
    const renderNodes = (nodes: any[]): any => nodes.map((node) => (
      <div key={node.key}>
        {node.title}
        {node.children?.length ? renderNodes(node.children) : null}
      </div>
    ))
    return <div>{renderNodes(treeData)}</div>
  },
}))
vi.mock('@/components/Pagination', () => ({ default: () => <div /> }))
vi.mock('./CaseDrawer', () => ({ default: () => null }))
vi.mock('./VersionDialog', () => ({ default: () => null }))

import TestCasePage from './index'

describe('用例批量删除确认', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.batchDeleteCases.mockResolvedValue({})
    useAuthStore.setState({
      permissions: ['*'],
      projects: [{ id: 61, code: 'batch-61', name: 'Batch 61 安全项目' }],
      currentProjectId: 61,
    })
  })

  it('确认前不提交，确认后按当前页选中范围提交', async () => {
    render(<TestCasePage />)

    fireEvent.click(await screen.findByRole('checkbox', { name: '选择当前页全部用例' }))
    fireEvent.click(screen.getByRole('button', { name: '批量删除 (2)' }))

    expect(screen.getByRole('heading', { name: '确认批量删除用例？' })).toBeTruthy()
    expect(screen.getByText(/Batch 61 安全项目/)).toBeTruthy()
    expect(api.batchDeleteCases).not.toHaveBeenCalled()

    fireEvent.click(screen.getByRole('button', { name: '确认删除' }))

    await waitFor(() => expect(api.batchDeleteCases).toHaveBeenCalledWith([12, 11]))
  })

  it('默认展示功能用例，并提供全部规范用例类型入口', () => {
    render(<TestCasePage />)

    expect(screen.getByRole('button', { name: /功能用例/ }).getAttribute('aria-pressed')).toBe('true')
    expect(screen.getByRole('button', { name: /^接口用例 \(/ })).toBeTruthy()
    expect(screen.getByRole('button', { name: /^UI 自动化 \(/ })).toBeTruthy()
    expect(screen.getByRole('button', { name: /^全部 \(/ })).toBeTruthy()
  })

  it('按界面和异常性质提供规范化筛选，并显示场景标签', () => {
    render(<TestCasePage />)

    expect(screen.getByRole('combobox', { name: '按产品界面筛选' })).toBeTruthy()
    expect(screen.getByRole('combobox', { name: '按用例场景筛选' })).toBeTruthy()
    expect(screen.getByText('正向')).toBeTruthy()
    expect(screen.getByText('负向')).toBeTruthy()
  })

  it('显式展示父模块直属用例，使父子计数可以完整对账', () => {
    render(<TestCasePage />)

    const directRows = screen.getAllByText('直属用例')
    const counts = directRows.map((el) => el.parentElement?.textContent || '')
    // FAQ帮助 27 = 直属 18 + 子级 9；赛事详情 20 = 直属 3 + 子级 17；
    // 订单列表（二级模块）12 = 直属 5 + 子级 7 —— 证明规则对任意业务域与任意层模块生效。
    expect(counts).toEqual(expect.arrayContaining([
      '直属用例 (18)',
      '直属用例 (3)',
      '直属用例 (5)',
    ]))
    // 叶子模块不出现 0 或重复核算行。
    expect(directRows).toHaveLength(3)
  })

  it('取消批量删除时产生零写请求', async () => {
    render(<TestCasePage />)

    fireEvent.click(await screen.findByRole('checkbox', { name: '选择当前页全部用例' }))
    fireEvent.click(screen.getByRole('button', { name: '批量删除 (2)' }))
    fireEvent.click(screen.getByRole('button', { name: '取消' }))

    expect(api.batchDeleteCases).not.toHaveBeenCalled()
    expect(screen.queryByRole('heading', { name: '确认批量删除用例？' })).toBeNull()
  })

  it('快速重复确认只提交一次批量删除', async () => {
    let resolveDelete: (() => void) | undefined
    api.batchDeleteCases.mockImplementation(() => new Promise<void>((resolve) => {
      resolveDelete = resolve
    }))
    render(<TestCasePage />)

    fireEvent.click(await screen.findByRole('checkbox', { name: '选择当前页全部用例' }))
    fireEvent.click(screen.getByRole('button', { name: '批量删除 (2)' }))
    const confirm = screen.getByRole('button', { name: '确认删除' })
    fireEvent.click(confirm)
    fireEvent.click(confirm)

    expect(api.batchDeleteCases).toHaveBeenCalledTimes(1)
    resolveDelete?.()
    await waitFor(() => expect(screen.queryByRole('heading', { name: '确认批量删除用例？' })).toBeNull())
  })

  it('服务端原子失败时保留删除范围供复核', async () => {
    api.batchDeleteCases.mockRejectedValue(new Error('atomic rollback'))
    render(<TestCasePage />)

    fireEvent.click(await screen.findByRole('checkbox', { name: '选择当前页全部用例' }))
    fireEvent.click(screen.getByRole('button', { name: '批量删除 (2)' }))
    fireEvent.click(screen.getByRole('button', { name: '确认删除' }))

    await waitFor(() => expect(api.batchDeleteCases).toHaveBeenCalledTimes(1))
    expect(screen.getByRole('heading', { name: '确认批量删除用例？' })).toBeTruthy()
    expect(screen.getByText(/2 条用例/)).toBeTruthy()
  })
})
