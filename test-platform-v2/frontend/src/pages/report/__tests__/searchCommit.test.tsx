import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const api = vi.hoisted(() => ({
  fetchReports: vi.fn(),
  fetchReport: vi.fn(),
  fetchTrends: vi.fn(),
  createReport: vi.fn(),
  deleteReport: vi.fn(),
  fetchTemplates: vi.fn(),
  fetchPlans: vi.fn(),
  fetchCoverage: vi.fn(),
}))

vi.mock('@/api/trace', () => ({ fetchCoverage: (...args: unknown[]) => api.fetchCoverage(...args) }))

vi.mock('sonner', () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}))

vi.mock('@/api/report', () => ({
  fetchReports: (...args: unknown[]) => api.fetchReports(...args),
  fetchReport: (...args: unknown[]) => api.fetchReport(...args),
  fetchTrends: (...args: unknown[]) => api.fetchTrends(...args),
  createReport: (...args: unknown[]) => api.createReport(...args),
  deleteReport: (...args: unknown[]) => api.deleteReport(...args),
  exportReportUrl: () => '',
}))

vi.mock('@/api/reportTemplate', () => ({
  fetchTemplates: (...args: unknown[]) => api.fetchTemplates(...args),
}))

vi.mock('@/api/testplan', () => ({
  fetchPlans: (...args: unknown[]) => api.fetchPlans(...args),
}))

vi.mock('@/hooks/useDocumentTitle', () => ({
  useDocumentTitle: () => {},
}))

vi.mock('@/hooks/use-chart-colors', () => ({
  useChartColors: () => [],
}))

vi.mock('@/components/charts/ChartFrame', () => ({
  default: () => <div data-testid="chart" />,
}))

vi.mock('@/components/StatCard', () => ({
  default: () => <div data-testid="stat-card" />,
}))

vi.mock('@/components/DataTable', () => ({
  default: ({ toolbar }: { toolbar?: React.ReactNode }) => (
    <div data-testid="report-table">{toolbar}</div>
  ),
}))

vi.mock('@/components/state', () => ({
  AsyncState: ({
    children,
    data,
  }: {
    children: React.ReactNode | ((data?: unknown) => React.ReactNode)
    data?: unknown
  }) => (
    <div>
      {typeof children === 'function'
        ? data === undefined
          ? <div data-testid="async-pending" />
          : (children as (d: unknown) => React.ReactNode)(data)
        : children}
    </div>
  ),
  ErrorState: () => null,
}))

import ReportPage from '../index'
import { useAuthStore } from '@/stores/auth'

describe('报告中心搜索提交态（B60-P2-001）', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.fetchReports.mockResolvedValue({ total: 0, items: [], page: 1, page_size: 20 })
    api.fetchTrends.mockResolvedValue({
      points: [],
      summary: { total_reports: 0, avg_pass_rate: 0 },
    })
    api.fetchPlans.mockResolvedValue([])
    api.fetchTemplates.mockResolvedValue([])
    api.fetchCoverage.mockImplementation(() => new Promise(() => {}))
    useAuthStore.setState({ permissions: ['*'], currentProjectId: 1 })
  })

  it('输入关键字不触发请求，仅提交触发一次有效 GET', async () => {
    render(
      <MemoryRouter>
        <ReportPage />
      </MemoryRouter>,
    )

    await waitFor(() => expect(api.fetchReports).toHaveBeenCalledTimes(1))

    const input = await screen.findByPlaceholderText('搜索报告名称')
    fireEvent.change(input, { target: { value: '回归' } })
    await new Promise((resolve) => setTimeout(resolve, 50))
    expect(api.fetchReports).toHaveBeenCalledTimes(1)

    fireEvent.click(screen.getByRole('button', { name: '搜索' }))
    await waitFor(() => expect(api.fetchReports).toHaveBeenCalledTimes(2))
    expect(api.fetchReports).toHaveBeenLastCalledWith({
      page: 1,
      page_size: 20,
      keyword: '回归',
    }, expect.any(AbortSignal))

    fireEvent.change(input, { target: { value: '回归2' } })
    fireEvent.keyDown(input, { key: 'Enter' })
    await waitFor(() => expect(api.fetchReports).toHaveBeenCalledTimes(3))
    expect(api.fetchReports).toHaveBeenLastCalledWith({
      page: 1,
      page_size: 20,
      keyword: '回归2',
    }, expect.any(AbortSignal))
  })

  it('只读角色不显示生成报告入口（B60-P1-009）', async () => {
    useAuthStore.setState({ permissions: ['report:list'] })
    render(
      <MemoryRouter>
        <ReportPage />
      </MemoryRouter>,
    )
    await waitFor(() => expect(api.fetchReports).toHaveBeenCalledTimes(1))
    expect(screen.queryByRole('button', { name: '生成报告' })).toBeNull()
  })

  it('追溯深链接不加载报告和趋势，切换时取消离开视图的请求', async () => {
    render(<MemoryRouter initialEntries={['/report?tab=trace']}><ReportPage /></MemoryRouter>)
    await waitFor(() => expect(api.fetchCoverage).toHaveBeenCalledTimes(1))
    expect(api.fetchReports).not.toHaveBeenCalled()
    expect(api.fetchTrends).not.toHaveBeenCalled()
    const coverageSignal = api.fetchCoverage.mock.calls[0][0] as AbortSignal
    fireEvent.mouseDown(screen.getByRole('tab', { name: '报告中心' }), { button: 0, ctrlKey: false })
    await waitFor(() => expect(api.fetchReports).toHaveBeenCalledTimes(1))
    expect(coverageSignal.aborted).toBe(true)
    expect(api.fetchTrends).toHaveBeenCalledTimes(1)
    const reportsSignal = api.fetchReports.mock.calls[0][1] as AbortSignal
    const trendsSignal = api.fetchTrends.mock.calls[0][0] as AbortSignal
    fireEvent.mouseDown(screen.getByRole('tab', { name: '质量追溯' }), { button: 0, ctrlKey: false })
    await waitFor(() => expect(api.fetchCoverage).toHaveBeenCalledTimes(2))
    expect(reportsSignal.aborted).toBe(true)
    expect(trendsSignal.aborted).toBe(true)
    expect(api.fetchReports).toHaveBeenCalledTimes(1)
  })
})
