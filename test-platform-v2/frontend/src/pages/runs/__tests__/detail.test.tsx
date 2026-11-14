import { cleanup, render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import RunDetailPage from '../detail'

const mocks = vi.hoisted(() => ({
  getAiqeRun: vi.fn(),
  listRunNodes: vi.fn(),
}))

vi.mock('@/api/aiqeRuns', () => ({
  getAiqeRun: mocks.getAiqeRun,
  listRunNodes: mocks.listRunNodes,
}))

vi.mock('../useRunEvents', () => ({
  useRunEvents: () => ({ events: [], connection: 'polling' }),
}))

function run() {
  return {
    id: 'run-1',
    run_key: 'RUN-1',
    source_type: 'manual',
    status: 'COMPLETED',
    outcome: 'FAIL',
    build_ref: 'b1',
    commit_sha: 'abc',
    created_at: '2026-11-14T00:00:00Z',
    started_at: null,
    finished_at: null,
    duration_ms: 12,
  }
}

function nodes() {
  return {
    run_id: 'run-1',
    status: 'COMPLETED',
    outcome: 'FAIL',
    nodes: [
      {
        node: {
          id: 'n1',
          node_key: 'login',
          driver_key: 'http',
          status: 'PASSED',
          error_class: '',
          attempt_count: 1,
          inputs: { url: 'https://api.test/login' },
          outputs: { token: 't-1' },
          secret_keys: ['API_KEY'],
          source_refs: [],
          started_at: null,
          finished_at: null,
        },
        attempts: [
          {
            id: 'a1',
            attempt_no: 1,
            status: 'PASSED',
            started_at: null,
            finished_at: null,
            error: null,
            output: { token: 't-1' },
            assertions: [
              {
                id: 'as1',
                assertion_key: 'status',
                type: 'http_status',
                status: 'PASS',
                schema_version: '1.0',
                oracle_layer: 'STD',
                oracle_ref: 'STD-200',
                severity: 'P0',
                expected: 200,
                actual: 200,
                actual_source: '',
                duration_ms: 1,
                timeout_ms: 0,
                error: '',
                artifact_refs: [],
              },
            ],
          },
        ],
        artifacts: [
          {
            id: 'art1',
            artifact_type: 'request',
            sha256: 'f'.repeat(64),
            size_bytes: 10,
            mime_type: 'application/json',
            redaction_status: 'sanitized',
            created_at: '2026-11-14T00:00:00Z',
          },
        ],
      },
    ],
  }
}

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/runs/run-1']}>
      <Routes>
        <Route path="/runs/:runId" element={<RunDetailPage />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('RunDetailPage（v1.4 步骤/断言可见）', () => {
  beforeEach(() => {
    mocks.getAiqeRun.mockReset()
    mocks.listRunNodes.mockReset()
    mocks.getAiqeRun.mockResolvedValue({ run: run(), events: [], artifacts: [] })
    mocks.listRunNodes.mockResolvedValue(nodes())
  })
  afterEach(cleanup)

  it('渲染节点、attempt、断言 expected/actual 与证据计数', async () => {
    renderPage()
    expect(await screen.findByText('login')).toBeTruthy()
    expect(screen.getByText('执行步骤（1）')).toBeTruthy()
    expect(screen.getByText('STD:STD-200')).toBeTruthy()
    expect(screen.getByText('PASS')).toBeTruthy()
    expect(screen.getByText(/attempts 1 · artifacts 1/)).toBeTruthy()
  })

  it('展示 BLOCKED/FAILED 不被当成 PASS', async () => {
    const data = nodes()
    data.nodes[0].node.status = 'BLOCKED'
    data.nodes[0].node.error_class = 'CAPABILITY_UNAVAILABLE'
    data.nodes[0].attempts[0].assertions[0].status = 'NOT_EVALUATED'
    mocks.listRunNodes.mockResolvedValue(data)
    renderPage()
    expect(await screen.findByText('BLOCKED')).toBeTruthy()
    expect(screen.getByText('CAPABILITY_UNAVAILABLE')).toBeTruthy()
    expect(screen.getByText('NOT_EVALUATED')).toBeTruthy()
  })
})
