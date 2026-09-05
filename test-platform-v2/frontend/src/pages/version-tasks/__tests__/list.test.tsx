import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import VersionTaskListPage from '../list'

const mocks = vi.hoisted(() => ({
  listVersionTasks: vi.fn(),
}))

vi.mock('@/api/versionTask', () => ({
  listVersionTasks: mocks.listVersionTasks,
}))

function makeTask(overrides: Record<string, unknown> = {}) {
  return {
    id: 7,
    project_id: 13,
    title: '体育 16.0.0 提测验收',
    version: '16.0.0',
    source: 'manual',
    status: 'plan_review',
    verdict: '',
    coverage: { pass: 3, fail: 1, skip: 0, blocked: 0 },
    summary: '',
    scope: {},
    risk: [],
    qa_owner_id: 0,
    created_at: '2026-09-05T02:00:00Z',
    updated_at: '2026-09-05T03:00:00Z',
    ...overrides,
  }
}

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/version-tasks']}>
      <Routes>
        <Route path="/version-tasks" element={<VersionTaskListPage />} />
        <Route path="/version-tasks/new" element={<div>建任务向导</div>} />
        <Route path="/version-tasks/:taskId" element={<div>执行与证据页</div>} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('VersionTaskListPage（DEF-20260905-002 列表可达）', () => {
  beforeEach(() => {
    mocks.listVersionTasks.mockReset()
    mocks.listVersionTasks.mockResolvedValue({ total: 0, page: 1, page_size: 20, items: [] })
  })
  afterEach(cleanup)

  it('渲染任务并把状态/结论映射为中文，覆盖列显示通过率', async () => {
    mocks.listVersionTasks.mockResolvedValue({
      total: 2,
      page: 1,
      page_size: 20,
      items: [
        makeTask(),
        makeTask({ id: 8, title: '体育 15.0.0 回归', version: '15.0.0', status: 'blocked', verdict: 'blocked', coverage: {} }),
      ],
    })
    renderPage()

    expect(await screen.findByText('体育 16.0.0 提测验收')).toBeTruthy()
    expect(screen.getByText('待评审')).toBeTruthy()
    expect(screen.getByText('已阻塞')).toBeTruthy()
    expect(screen.getByText('打回')).toBeTruthy()
    expect(screen.getByText('3/4')).toBeTruthy()
    // 空结论与无覆盖数据都显 —：不得留空，也不得渲染成 0/0（会被读成「跑了 0 个且通过 0 个」）
    expect(screen.getAllByText('—')).toHaveLength(2)
    expect(screen.queryByText('plan_review')).toBeNull()
    expect(screen.queryByText('blocked')).toBeNull()
  })

  it('无任务时显示空态与新建入口', async () => {
    renderPage()

    expect(await screen.findByText('暂无版本验收任务')).toBeTruthy()
    expect(screen.getAllByText('新建版本任务').length).toBeGreaterThan(0)
  })

  it('加载失败时显示错误态而不是空表格', async () => {
    mocks.listVersionTasks.mockRejectedValue(new Error('网关超时'))
    renderPage()

    expect(await screen.findByText('版本验收任务加载失败')).toBeTruthy()
    expect(screen.queryByText('暂无版本验收任务')).toBeNull()
    expect(screen.getByRole('button', { name: '重新加载' })).toBeTruthy()
  })

  it('请求携带 AbortSignal，卸载时取消在途请求', async () => {
    const { unmount } = renderPage()
    await screen.findByText('暂无版本验收任务')

    const signal = mocks.listVersionTasks.mock.calls[0][2] as AbortSignal
    expect(signal).toBeInstanceOf(AbortSignal)
    expect(signal.aborted).toBe(false)

    unmount()
    expect(signal.aborted).toBe(true)
  })

  it('关键字输入防抖为一次请求，且回到第 1 页', async () => {
    renderPage()
    await screen.findByText('暂无版本验收任务')
    expect(mocks.listVersionTasks).toHaveBeenCalledTimes(1)

    const input = screen.getByLabelText('搜索')
    fireEvent.change(input, { target: { value: 'a' } })
    fireEvent.change(input, { target: { value: 'ab' } })
    fireEvent.change(input, { target: { value: 'abc' } })

    await waitFor(
      () => {
        expect(mocks.listVersionTasks).toHaveBeenCalledTimes(2)
      },
      { timeout: 1500 },
    )
    expect(mocks.listVersionTasks).toHaveBeenLastCalledWith('', 'abc', expect.any(AbortSignal), 1, 20)
  })

  it('状态筛选下拉带无障碍名称，行点击可进入执行与证据页', async () => {
    mocks.listVersionTasks.mockResolvedValue({
      total: 1,
      page: 1,
      page_size: 20,
      items: [makeTask()],
    })
    renderPage()

    const title = await screen.findByText('体育 16.0.0 提测验收')
    expect(screen.getByLabelText('按状态筛选')).toBeTruthy()
    expect(screen.getByRole('link', { name: '新建版本任务' })).toBeTruthy()

    fireEvent.click(title)
    expect(await screen.findByText('执行与证据页')).toBeTruthy()
  })
})
