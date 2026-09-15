import { fireEvent, render, screen, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const fetchApiExecutionTasks = vi.fn()
const fetchApiExecutionTask = vi.fn()

vi.mock('@/api/apitest', () => ({
  fetchApiExecutionTasks: (...args: any[]) => fetchApiExecutionTasks(...args),
  fetchApiExecutionTask: (...args: any[]) => fetchApiExecutionTask(...args),
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
  })

  it('shows historical tasks as read-only with detail access only', async () => {
    render(
      <MemoryRouter>
        <TaskTab />
      </MemoryRouter>,
    )

    expect(await screen.findByText('夜间回归')).toBeTruthy()
    expect(screen.getByText('历史执行记录只读')).toBeTruthy()
    expect(screen.getByRole('button', { name: '前往执行中心' })).toBeTruthy()
    expect(screen.queryByRole('button', { name: /取消.*夜间回归/ })).toBeNull()
    expect(screen.queryByRole('button', { name: /重跑.*夜间回归/ })).toBeNull()
    expect(screen.queryByRole('button', { name: /删除.*夜间回归/ })).toBeNull()

    const detailButton = screen.getByRole('button', { name: /查看.*夜间回归.*详情/ })
    fireEvent.click(detailButton)
    expect(await screen.findByText('用例 #7')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: '展开' }))

    const copyButton = screen.getByRole('button', { name: '复制 curl' })
    expect(copyButton.getAttribute('aria-label')).toBe('复制 curl')
  })

  it('stacks task content into non-overlapping rows on narrow screens', async () => {
    render(
      <MemoryRouter>
        <TaskTab />
      </MemoryRouter>,
    )

    const row = await screen.findByTestId('api-task-row-9')
    expect(row.className).toContain('flex-col')
    expect(row.className).toContain('sm:flex-row')

    const meta = within(row).getByTestId('api-task-row-meta')
    expect(meta.className).toContain('w-full')
    expect(meta.className).toContain('flex-wrap')
    expect(meta.className).toContain('sm:w-auto')
  })
})
