import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const fetchRunReplay = vi.fn()

vi.mock('@/api/executions', async (loadOriginal) => {
  const original = await loadOriginal<typeof import('@/api/executions')>()
  return { ...original, fetchRunReplay: (...args: unknown[]) => fetchRunReplay(...args) }
})

import ReplayPage from './replay'

describe('Execution replay labels', () => {
  beforeEach(() => {
    fetchRunReplay.mockReset()
    fetchRunReplay.mockResolvedValue({
      manifest: {},
      hash: '1234567890abcdef',
      view: {
        outcome: 'PASS',
        runtime_status: 'FINISHED',
        environment_snapshot_id: 5,
        timeline: [{
          id: 11,
          run_id: 301,
          sequence: 1,
          step_key: '打开篮球首页',
          step_type: 'UI',
          status: 'SUCCEEDED',
        }],
        assertions: [],
        evidence: [{
          id: 21,
          project_id: 1,
          run_id: 301,
          evidence_type: 'SCREENSHOT',
          storage_provider: 'local',
          storage_uri: '/evidence/functional-case.png',
          content_hash: 'abcdef1234567890',
          content_type: 'image/png',
          size_bytes: 458644,
          sanitization_status: 'SANITIZED',
          sensitivity: 'INTERNAL',
          retention_class: 'standard',
          integrity_status: 'VERIFIED',
          created_at: '2026-09-07T10:00:00Z',
        }],
      },
    })
  })

  it('shows localized replay and evidence facts', async () => {
    render(
      <MemoryRouter initialEntries={['/executions/301/replay']}>
        <Routes>
          <Route path="/executions/:runId/replay" element={<ReplayPage />} />
        </Routes>
      </MemoryRouter>,
    )

    expect((await screen.findAllByText('打开篮球首页')).length).toBeGreaterThanOrEqual(2)
    expect(screen.getAllByText('成功').length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText('截图').length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText('已脱敏').length).toBeGreaterThanOrEqual(2)
    expect(screen.getByText('内部')).toBeTruthy()
    expect(screen.queryByText('SUCCEEDED')).toBeNull()
    expect(screen.queryByText('SCREENSHOT')).toBeNull()
  })
})
