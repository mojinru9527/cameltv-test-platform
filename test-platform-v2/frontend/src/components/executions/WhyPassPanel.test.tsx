import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import WhyPassPanel from './WhyPassPanel'
import type { Run, Assertion, Step, Evidence } from '@/api/executions'

function makeRun(overrides: Partial<Run> = {}): Run {
  return {
    id: 1,
    project_id: 1,
    mission_id: 1,
    scenario_id: 1,
    scenario_version_id: 1,
    contract_version_id: 1,
    environment_id: 1,
    runtime_status: 'FINISHED',
    outcome: 'PASS',
    evidence_status: 'COMPLETE',
    trigger_type: 'MANUAL',
    retry_no: 0,
    created_by: 9,
    created_at: null,
    ...overrides,
  }
}

const assertions: Assertion[] = [
  { id: 1, run_id: 1, oracle_id: 5, result: 'PASS', reason_code: 'eq', evidence_refs_json: '[]' },
  { id: 2, run_id: 1, oracle_id: 6, result: 'PASS', reason_code: 'contains', evidence_refs_json: '[]' },
]
const steps: Step[] = [
  { id: 10, run_id: 1, sequence: 1, step_key: 'login', step_type: 'API', status: 'SUCCEEDED' },
]
const evidence: Evidence[] = [
  { id: 30, project_id: 1, run_id: 1, evidence_type: 'RESPONSE', storage_provider: 'local', storage_uri: '/p/1', content_hash: 'h', content_type: 'application/json', size_bytes: 10, sanitization_status: 'SANITIZED', sensitivity: 'normal', retention_class: 'standard', created_at: null },
]

describe('WhyPassPanel', () => {
  it('renders a PASS explanation with assertion + evidence counts', () => {
    render(<WhyPassPanel run={makeRun()} assertions={assertions} steps={steps} evidence={evidence} />)
    expect(screen.getByText('通过')).toBeTruthy()
    expect(screen.getByText('该执行判定为通过，理由如下。')).toBeTruthy()
    // PASS must enumerate why: assertion pass count, evidence count
    expect(screen.getByText(/断言通过 2 \/ 2 条/)).toBeTruthy()
    expect(screen.getByText(/采集证据 1 条/)).toBeTruthy()
  })
})
