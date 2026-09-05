import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import MissionContractPage from '../contract'

const mocks = vi.hoisted(() => ({
  fetchMissionAmbiguities: vi.fn(),
  fetchCurrentContract: vi.fn(),
}))

vi.mock('@/api/ambiguities', () => ({
  analyzeMissionAmbiguities: vi.fn(),
  fetchMissionAmbiguities: mocks.fetchMissionAmbiguities,
  resolveAmbiguity: vi.fn(),
  AMBIGUITY_STATUS_LABELS: {},
}))

vi.mock('@/api/contract', () => ({
  generateContract: vi.fn(),
  fetchCurrentContract: mocks.fetchCurrentContract,
  freezeContract: vi.fn(),
  CONTRACT_STATUS_LABELS: {
    DRAFT: { label: '草稿', color: '' },
    FROZEN: { label: '已冻结', color: '' },
  },
  CONTRACT_RULE_KIND_LABEL: { BUSINESS_RULE: '业务规则' },
  CONTRACT_SOURCE_TYPE_LABEL: { RULE_BASELINE: '规则基线' },
}))

function makeVersion(snapshot: unknown) {
  return {
    id: 2,
    contract_id: 2,
    version_no: 2,
    status: 'DRAFT',
    content_hash: 'hash',
    snapshot,
    created_at: null,
    approved_at: null,
  }
}

function makeSnapshot(rules: unknown[]) {
  return {
    schema_version: '1.0',
    mission_id: 3,
    scope_revision: 'scope-hash-2',
    rules,
    required_outcomes: [{ outcome_key: 'outcome-i1', statement: '会员权益恢复' }],
  }
}

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/missions/3/contract']}>
      <Routes>
        <Route path="/missions/:id/contract" element={<MissionContractPage />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('MissionContractPage', () => {
  beforeEach(() => {
    mocks.fetchMissionAmbiguities.mockReset()
    mocks.fetchCurrentContract.mockReset()
    mocks.fetchMissionAmbiguities.mockResolvedValue([])
    mocks.fetchCurrentContract.mockResolvedValue({
      contract_id: 2,
      name: '体育 16.0.0 Contract',
      version_no: 2,
      version: {
        id: 2,
        contract_id: 2,
        version_no: 2,
        status: 'FROZEN',
        content_hash: 'hash',
        created_at: null,
        approved_at: null,
      },
    })
  })

  it('loads contract and ambiguity collections once on mount', async () => {
    renderPage()

    await screen.findByText('v2')
    await waitFor(() => {
      expect(mocks.fetchMissionAmbiguities).toHaveBeenCalledTimes(1)
      expect(mocks.fetchCurrentContract).toHaveBeenCalledTimes(1)
    })
    expect(mocks.fetchMissionAmbiguities.mock.calls[0][0]).toBe(3)
    expect(mocks.fetchCurrentContract.mock.calls[0][0]).toBe(3)
  })

  // --- Batch 230 S1 / DEF-20260905-001 ---

  it('renders snapshot rules with Chinese kind labels and a distinguishable severity ladder', async () => {
    mocks.fetchCurrentContract.mockResolvedValue({
      contract_id: 2,
      name: 'C',
      version_no: 2,
      version: makeVersion(
        makeSnapshot([
          {
            rule_key: 'rule-scope-1-1',
            title: '会员续费后恢复权益',
            kind: 'BUSINESS_RULE',
            statement: '续费成功即恢复',
            risk_level: 'P0',
            source_type: 'RULE_BASELINE',
          },
          {
            rule_key: 'rule-scope-1-2',
            title: '赛事比分实时刷新',
            kind: 'BUSINESS_RULE',
            statement: '',
            risk_level: 'P1',
            source_type: 'RULE_BASELINE',
          },
        ]),
      ),
    })

    renderPage()

    expect(await screen.findByText('会员续费后恢复权益')).toBeTruthy()
    expect(screen.getByText('赛事比分实时刷新')).toBeTruthy()
    // 裸英文枚举不得出现，四级严重度必须可辨（Red Flag #1 / #3）
    expect(screen.getAllByText('业务规则')).toHaveLength(2)
    expect(screen.getByText('P0-致命')).toBeTruthy()
    expect(screen.getByText('P1-严重')).toBeTruthy()
    expect(screen.getAllByText('规则基线')).toHaveLength(2)
    // 必需产出
    expect(screen.getByText('outcome-i1')).toBeTruthy()
    expect(screen.getByText('会员权益恢复')).toBeTruthy()
  })

  it('blocks freezing an empty shell contract and says why', async () => {
    mocks.fetchCurrentContract.mockResolvedValue({
      contract_id: 2,
      name: 'C',
      version_no: 2,
      version: makeVersion(makeSnapshot([])),
    })

    renderPage()

    expect(await screen.findByText(/快照无有效规则/)).toBeTruthy()
    const freeze = screen.getByRole('button', { name: /冻结契约/ }) as HTMLButtonElement
    expect(freeze.disabled).toBe(true)
  })

  it('renders ErrorState instead of downgrading a failure to empty data', async () => {
    mocks.fetchCurrentContract.mockRejectedValue(new Error('服务器错误'))

    renderPage()

    expect(await screen.findByText('契约页加载失败')).toBeTruthy()
    expect(screen.getByRole('button', { name: '重新加载' })).toBeTruthy()
    expect(screen.queryByText(/快照无有效规则/)).toBeNull()
  })

  it('keeps "not generated yet" as an empty state, not an error', async () => {
    mocks.fetchCurrentContract.mockResolvedValue(null)

    renderPage()

    expect(await screen.findByText('尚未生成 Test Contract。')).toBeTruthy()
    expect(screen.queryByText('契约页加载失败')).toBeNull()
  })
})
