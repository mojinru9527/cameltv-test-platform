import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import ImpactTab from '../components/ImpactTab'
import type { ImpactResult } from '@/api/impact'

const mockState: {
  data: ImpactResult | undefined
  isLoading: boolean
  isError: boolean
  error: Error | null
} = { data: undefined, isLoading: false, isError: false, error: null }
const refetch = vi.fn()

vi.mock('@/hooks/useApi', () => ({
  useApi: () => ({
    data: mockState.data,
    isLoading: mockState.isLoading,
    isRefetching: false,
    isError: mockState.isError,
    error: mockState.error,
    refetch,
    setData: vi.fn(),
    abort: vi.fn(),
  }),
}))

const RESULT: ImpactResult = {
  project_id: 1,
  query: { module: '体育', version: '' },
  affected_modules: ['体育直播', '体育积分'],
  cases: {
    functional: [{ case_id: 3, title: '积分展示', module: '体育积分', case_type: 'manual', ref: 'case:3' }],
    api: [{ case_id: 1, title: '首页列表', module: '体育直播', case_type: 'api', ref: 'case:1' }],
    ui: [{ case_id: 2, title: '轮播可见', module: '体育直播', case_type: 'ui', ref: 'case:2' }],
  },
  counts: { affected_modules: 2, functional: 1, api: 1, ui: 1, cases_total: 3, gaps: 1 },
  last_runs: [{ case_id: 1, plan_id: 9, status: 'fail', executed_at: '2026-09-18T10:00:00', ref: 'plan:9' }],
  gaps: ['体育积分'],
  refs: { modules: ['module:体育直播', 'module:体育积分'], cases: ['case:1', 'case:2', 'case:3'] },
}

function renderTab() {
  return render(
    <MemoryRouter>
      <ImpactTab />
    </MemoryRouter>,
  )
}

function search(moduleName = '体育') {
  fireEvent.change(screen.getByLabelText('变更模块名'), { target: { value: moduleName } })
  fireEvent.click(screen.getByRole('button', { name: '查询要跑哪些' }))
}

beforeEach(() => {
  mockState.data = undefined
  mockState.isLoading = false
  mockState.isError = false
  mockState.error = null
  refetch.mockClear()
})

describe('ImpactTab（Batch 260 / B3-3 前端视图）', () => {
  it('未查询时不猜结论，给出明确引导', () => {
    renderTab()
    expect(screen.getByText(/输入模块名后查询/)).toBeTruthy()
    expect(screen.queryByTestId('impact-result')).toBeNull()
  })

  it('渲染受影响模块、三类用例、最近执行与缺口', () => {
    mockState.data = RESULT
    renderTab()
    search()
    expect(screen.getByTestId('impact-result')).toBeTruthy()
    expect(screen.getByText('体育直播')).toBeTruthy()
    expect(screen.getByText('积分展示')).toBeTruthy()
    expect(screen.getByText('plan:9')).toBeTruthy()
    expect(screen.getByTestId('impact-gaps')).toBeTruthy()
  })

  it('每条结论都带可回溯引用（case:/plan:）', () => {
    mockState.data = RESULT
    renderTab()
    search()
    for (const ref of ['case:1', 'case:2', 'case:3', 'plan:9']) {
      expect(screen.getByText(ref)).toBeTruthy()
    }
  })

  it('无关联时显示空态与原因，而不是空白', () => {
    mockState.data = {
      ...RESULT,
      affected_modules: [],
      cases: { functional: [], api: [], ui: [] },
      counts: { affected_modules: 0, functional: 0, api: 0, ui: 0, cases_total: 0, gaps: 0 },
      last_runs: [],
      gaps: [],
      refs: { modules: [], cases: [] },
      reason: '版本不存在或没有模块',
    }
    renderTab()
    search()
    expect(screen.getByTestId('impact-empty')).toBeTruthy()
    expect(screen.getByText(/版本不存在或没有模块/)).toBeTruthy()
  })

  it('无执行记录时明确说明，不显示为通过', () => {
    mockState.data = { ...RESULT, last_runs: [] }
    renderTab()
    search()
    expect(screen.getByText(/还没有执行记录/)).toBeTruthy()
  })

  it('加载中不显示空态（避免误判"没有关联"）', () => {
    mockState.isLoading = true
    renderTab()
    search()
    expect(screen.queryByTestId('impact-empty')).toBeNull()
  })
})
