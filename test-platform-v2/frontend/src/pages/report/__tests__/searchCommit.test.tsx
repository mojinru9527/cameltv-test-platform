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
}))

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
    })

    fireEvent.change(input, { target: { value: '回归2' } })
    fireEvent.keyDown(input, { key: 'Enter' })
    await waitFor(() => expect(api.fetchReports).toHaveBeenCalledTimes(3))
    expect(api.fetchReports).toHaveBeenLastCalledWith({
      page: 1,
      page_size: 20,
      keyword: '回归2',
    })
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
})
