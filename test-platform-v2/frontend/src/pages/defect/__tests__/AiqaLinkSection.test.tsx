import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import AiqaLinkSection from '../AiqaLinkSection'
import type { DefectItem } from '@/types'

function makeDefect(overrides: Partial<DefectItem> = {}): DefectItem {
  return {
    id: 1,
    defect_id: 'DEF-20261112-001',
    title: '直播入口点击无响应',
    description: '',
    severity: 'P1',
    status: 'open',
    case_id: null,
    execution_id: null,
    assignee_id: 0,
    assignee_name: '',
    external_id: '',
    external_url: '',
    creator_id: 0,
    creator_name: '',
    case_title: '',
    resolved_at: null,
    created_at: null,
    updated_at: null,
    aiqe_run_id: 'run-abc',
    aiqe_node_run_id: 'node-1',
    ac_refs: ['AC-001', 'AC-002'],
    reproduction_steps: [
      { action: '打开直播入口', expected: '入口可见', evidence_ref: 'artifact:dom-1' },
    ],
    evidence_refs: ['artifact:trace-1', 'event:104'],
    is_draft: true,
    ...overrides,
  }
}

describe('AiqaLinkSection', () => {
  it('展示 linked execution、AC、复现步骤与证据', () => {
    render(<AiqaLinkSection defect={makeDefect()} />)
    expect(screen.getByText('AIQE 关联执行')).toBeTruthy()
    expect(screen.getByText('run-abc')).toBeTruthy()
    expect(screen.getByText('node-1')).toBeTruthy()
    expect(screen.getByText('AC-001')).toBeTruthy()
    expect(screen.getByText('AC-002')).toBeTruthy()
    expect(screen.getByText(/打开直播入口/)).toBeTruthy()
    expect(screen.getByText('artifact:trace-1')).toBeTruthy()
    expect(screen.getByText('event:104')).toBeTruthy()
  })

  it('无 AIQE 关联时不渲染', () => {
    const { container } = render(
      <AiqaLinkSection defect={makeDefect({ aiqe_run_id: null })} />
    )
    expect(container.innerHTML).toBe('')
  })
})
