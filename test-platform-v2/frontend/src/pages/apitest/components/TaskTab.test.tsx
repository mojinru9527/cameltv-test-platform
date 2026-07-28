import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const fetchApiExecutionTasks = vi.fn()
const fetchApiExecutionTask = vi.fn()
const cancelApiExecutionTask = vi.fn()

vi.mock('@/api/apitest', () => ({
  fetchApiExecutionTasks: (...args: any[]) => fetchApiExecutionTasks(...args),
  fetchApiExecutionTask: (...args: any[]) => fetchApiExecutionTask(...args),
  cancelApiExecutionTask: (...args: any[]) => cancelApiExecutionTask(...args),
}))
vi.mock('sonner', () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}))

import TaskTab from './TaskTab'

const task = {
  id: 9,
  project_id: 1,
  task_id: 'API-TASK-9',
  name: '夜间回归',
  environment_id: null,
  service_id: null,
  status: 'running',
  total: 1,
  passed: 0,
  failed: 0,
  skipped: 0,
  trigger_type: 'manual',
  creator_id: 1,
  started_at: null,
  finished_at: null,
  created_at: null,
}

describe('API execution task controls', () => {
  beforeEach(() => {
    fetchApiExecutionTasks.mockReset().mockResolvedValue({
      items: [task],
      total: 1,
    })
    fetchApiExecutionTask.mockReset().mockResolvedValue({
      ...task,
      items: [
        {
          id: 3,
          task_id: 9,
          case_id: 7,
          status: 'passed',
          duration_ms: 15,
          request_snapshot: JSON.stringify({
            method: 'GET',
            url: 'https://example.com/health',
            curl: 'curl https://example.com/health',
          }),
          response_snapshot: '{}',
          assertion_results: '[]',
          error_message: '',
          created_at: null,
        },
      ],
    })
    cancelApiExecutionTask.mockReset().mockResolvedValue(undefined)
  })

  it('provides accessible names for icon-only task actions', async () => {
    render(<TaskTab />)

    expect(await screen.findByText('夜间回归')).toBeTruthy()
    expect(screen.getByRole('button', { name: '刷新执行任务' })).toBeTruthy()

    const detailButton = screen.getByRole('button', { name: /查看.*夜间回归.*详情/ })
    const cancelButton = screen.getByRole('button', { name: /取消.*夜间回归/ })
    fireEvent.click(cancelButton)
    await waitFor(() => expect(cancelApiExecutionTask).toHaveBeenCalledWith(9))

    fireEvent.click(detailButton)
    expect(await screen.findByText('用例 #7')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: '展开' }))

    const copyButton = screen.getByRole('button', { name: '复制 curl' })
    expect(copyButton.getAttribute('aria-label')).toBe('复制 curl')
  })
})
