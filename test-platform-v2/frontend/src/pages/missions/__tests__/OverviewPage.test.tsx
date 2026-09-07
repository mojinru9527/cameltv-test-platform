import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const mocks = vi.hoisted(() => ({
  fetchMission: vi.fn(),
  fetchMissionLifecycle: vi.fn(),
}))

vi.mock('@/api/missions', async (loadOriginal) => {
  const original = await loadOriginal<typeof import('@/api/missions')>()
  return {
    ...original,
    fetchMission: mocks.fetchMission,
    fetchMissionLifecycle: mocks.fetchMissionLifecycle,
  }
})

import MissionOverviewPage from '../overview'

const mission = {
  id: 34,
  project_id: 1,
  mission_key: 'M-1-0034',
  mission_type: 'FEATURE',
  title: '体育平台 16.0.0 篮球多项目适配',
  version_label: '16.0.0',
  status: 'SCENARIO_READY',
  owner_id: 1,
  qa_owner_id: 1,
  default_environment_id: 5,
  current_contract_version_id: 8,
  acceptance_status: 'PASS',
  legacy_version_mission_id: null,
  version_task_id: 6,
  created_by: 1,
  created_at: null,
  updated_at: null,
  archived_at: null,
}

const lifecycle = {
  mission: {
    id: 34,
    mission_type: 'FEATURE',
    status: 'SCENARIO_READY',
    acceptance_status: 'PASS',
    stored_acceptance_status: 'PASS',
    acceptance_consistent: true,
    version_task_id: 6,
  },
  version_task: { id: 6, title: '16.0.0 验收', version: '16.0.0', status: 'executing' },
  phases: [
    { mission_id: 34, mission_type: 'FEATURE', label: '需求测试', status: 'SCENARIO_READY', is_current: true },
    { mission_id: 35, mission_type: 'VERSION', label: '版本回归', status: 'DRAFT', is_current: false },
    { mission_id: 36, mission_type: 'REGRESSION', label: '生产回归', status: 'DRAFT', is_current: false },
  ],
  stages: [
    { key: 'sources', label: '资料', status: 'COMPLETE', total: 1, completed: 1, gap: '' },
    { key: 'analysis', label: '需求分析', status: 'COMPLETE', total: 4, completed: 4, gap: '' },
    { key: 'contract', label: '测试契约', status: 'COMPLETE', total: 1, completed: 1, gap: '' },
    { key: 'cases', label: '用例设计', status: 'COMPLETE', total: 3, completed: 3, gap: '' },
    { key: 'execution', label: '执行证据', status: 'IN_PROGRESS', total: 3, completed: 1, gap: '2 条用例尚无证据' },
    { key: 'acceptance', label: '验收结论', status: 'COMPLETE', total: 1, completed: 1, gap: '' },
  ],
  supporting_stages: [
    { key: 'builds', label: 'Build', status: 'COMPLETE', total: 1, completed: 1, gap: '' },
    { key: 'changes', label: '变化检测', status: 'COMPLETE', total: 1, completed: 1, gap: '' },
    { key: 'impact', label: '影响分析', status: 'COMPLETE', total: 1, completed: 1, gap: '' },
    { key: 'lineage', label: 'Lineage', status: 'COMPLETE', total: 1, completed: 1, gap: '' },
    { key: 'gaps', label: '场景缺口', status: 'COMPLETE', total: 1, completed: 1, gap: '' },
  ],
  integrity_status: 'INCOMPLETE',
  coverage: {
    case_types: { FUNCTIONAL: 1, API: 1, UI: 1, UNCLASSIFIED: 0 },
    requirement_roles: { NEW: 2, CHANGED: 0, IMPACTED_BASELINE: 1, UNCLASSIFIED: 0 },
  },
  totals: {
    cases: 3,
    runs: 2,
    evidence: 1,
    verified_evidence: 1,
    steps: 2,
    assertions: 2,
    replays: 1,
    defects: 1,
    retests: 1,
    executed_cases: 1,
  },
  cases: [
    {
      scenario_id: 10,
      scenario_version_id: 11,
      scenario_key: 'BASKETBALL-UI-001',
      title: '切换篮球项目',
      case_type: 'UI',
      requirement_role: 'NEW',
      module_key: '篮球/项目切换',
      review_status: 'APPROVED',
      source_ref_count: 1,
      source_refs_valid: true,
      content_complete: true,
      run_count: 2,
      latest_run_id: 13,
      latest_outcome: 'PASS',
      evidence_count: 1,
      verified_evidence_count: 1,
      step_count: 2,
      assertion_count: 2,
      replay_count: 1,
      execution_complete: true,
      defect_count: 1,
      retest_count: 1,
      retest_status: 'RETEST_PASSED',
    },
  ],
  artifacts: {
    fragments: 4,
    change_sets: 1,
    change_items: 2,
    impact_runs: 1,
    lineage_edges: 6,
    gap_candidates: 1,
    latest_change_set_id: 20,
    latest_impact_run_id: 30,
    latest_gate_result_id: 40,
  },
  gaps: ['2 条用例尚无证据'],
}

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/missions/34/overview']}>
        <Routes>
          <Route path="/missions/:id/overview" element={<MissionOverviewPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

beforeEach(() => {
  vi.clearAllMocks()
  mocks.fetchMission.mockResolvedValue(mission)
  mocks.fetchMissionLifecycle.mockResolvedValue(lifecycle)
})

describe('MissionOverviewPage lifecycle facts', () => {
  it('shows phases, six live stages, coverage and per-case traceability', async () => {
    renderPage()

    expect(await screen.findByText('需求测试')).toBeTruthy()
    expect(screen.getByText('版本回归')).toBeTruthy()
    expect(screen.getByText('生产回归')).toBeTruthy()
    for (const label of ['资料', '需求分析', '测试契约', '用例设计', '执行证据', '验收结论']) {
      expect(screen.getByText(label)).toBeTruthy()
    }
    expect(screen.getByText('功能 1')).toBeTruthy()
    expect(screen.getByText('接口 1')).toBeTruthy()
    expect(screen.getByText('UI 自动化 1')).toBeTruthy()
    expect(screen.getByText('切换篮球项目')).toBeTruthy()
    expect(screen.getByText('来源 1')).toBeTruthy()
    expect(screen.getByText('执行 2')).toBeTruthy()
    expect(screen.getByText('证据 1/1')).toBeTruthy()
    expect(screen.getByText('步骤 2')).toBeTruthy()
    expect(screen.getByText('断言 2')).toBeTruthy()
    expect(screen.getByText('回放 1')).toBeTruthy()
    expect(screen.getByText('缺陷 1')).toBeTruthy()
    expect(screen.getByText('复验通过')).toBeTruthy()
    expect(screen.getByText('2 条用例尚无证据')).toBeTruthy()
    expect(screen.getByText('验证资产')).toBeTruthy()
    expect(screen.queryByText('AI 分析 → Tester 评审')).toBeNull()
  })

  it('shows a retryable error instead of treating API failure as empty', async () => {
    mocks.fetchMissionLifecycle
      .mockRejectedValueOnce(new Error('生命周期加载失败'))
      .mockResolvedValueOnce(lifecycle)
    renderPage()

    expect(await screen.findByText('全链路数据加载失败')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: '重新加载' }))
    await waitFor(() => expect(mocks.fetchMissionLifecycle).toHaveBeenCalledTimes(2))
    expect(await screen.findByText('需求测试')).toBeTruthy()
  })
})
