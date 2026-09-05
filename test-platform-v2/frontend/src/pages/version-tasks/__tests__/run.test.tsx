import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router'
import { toast } from 'sonner'
import type { VersionTask, VersionTaskRun } from '@/api/versionTask'

const mocks = vi.hoisted(() => ({
  getVersionTask: vi.fn(),
  listRuns: vi.fn(),
  startRun: vi.fn(),
  getRegressionSet: vi.fn(),
  buildReleasePackage: vi.fn(),
  createDefectDraft: vi.fn(),
  syncDefect: vi.fn(),
  releaseTask: vi.fn(),
  notifyRelease: vi.fn(),
}))

vi.mock('@/api/versionTask', () => ({
  getVersionTask: mocks.getVersionTask,
  listRuns: mocks.listRuns,
  startRun: mocks.startRun,
  getRegressionSet: mocks.getRegressionSet,
  buildReleasePackage: mocks.buildReleasePackage,
  createDefectDraft: mocks.createDefectDraft,
  syncDefect: mocks.syncDefect,
  releaseTask: mocks.releaseTask,
  notifyRelease: mocks.notifyRelease,
}))

vi.mock('sonner', () => ({ toast: { success: vi.fn(), error: vi.fn() } }))

import VersionTaskRunPage from '../[taskId]'

function makeTask(overrides: Partial<VersionTask> = {}): VersionTask {
  return {
    id: 9,
    project_id: 13,
    title: '体育 16.0.0 验收',
    version: '16.0.0',
    status: 'executing',
    verdict: '',
    coverage: {},
    ...overrides,
  } as VersionTask
}

function makeRun(overrides: Partial<VersionTaskRun> = {}): VersionTaskRun {
  return {
    id: 1,
    task_id: 9,
    status: 'done',
    progress: 100,
    total: 1,
    passed: 1,
    failed: 0,
    skipped: 0,
    blocked: 0,
    evidence: [],
    failures: [],
    ...overrides,
  }
}

function renderPage(runs: VersionTaskRun[] = []) {
  mocks.getVersionTask.mockResolvedValue(makeTask())
  mocks.listRuns.mockResolvedValue(runs)
  mocks.getRegressionSet.mockResolvedValue([])
  mocks.buildReleasePackage.mockResolvedValue(null)

  return render(
    <MemoryRouter initialEntries={['/version-tasks/9']}>
      <Routes>
        <Route path="/version-tasks/:taskId" element={<VersionTaskRunPage />} />
      </Routes>
    </MemoryRouter>,
  )
}

beforeEach(() => {
  vi.clearAllMocks()
})

describe('一键运行的结果提示（DEF-20260905-003）', () => {
  it('零采纳项被阻塞时提示阻塞原因，不得报「运行完成」', async () => {
    mocks.startRun.mockResolvedValue(
      makeRun({
        status: 'blocked',
        total: 0,
        passed: 0,
        failures: [
          {
            item_id: 0,
            title: '整体运行',
            kind: 'plan',
            evidence: '',
            message: '本任务方案中没有已采纳/已修订的条目',
            http_status: null,
          },
        ],
      }),
    )
    renderPage()
    await waitFor(() => expect(mocks.listRuns).toHaveBeenCalled())

    fireEvent.click(screen.getByRole('button', { name: '一键运行' }))

    await waitFor(() => expect(mocks.startRun).toHaveBeenCalled())
    expect(toast.error).toHaveBeenCalledWith('运行被阻塞：没有可执行的方案条目')
    expect(toast.success).not.toHaveBeenCalled()
  })

  it('阻塞成因在环境侧时不得误报「没有可执行的方案条目」', async () => {
    mocks.startRun.mockResolvedValue(
      makeRun({
        status: 'blocked',
        total: 3,
        passed: 1,
        blocked: 2,
        failures: [
          { item_id: 1, title: '登录', kind: 'environment', evidence: '', message: '无可执行目标 URL' },
          { item_id: 2, title: '比分', kind: 'environment', evidence: '', message: '无可执行目标 URL' },
        ],
      }),
    )
    renderPage()
    await waitFor(() => expect(mocks.listRuns).toHaveBeenCalled())

    fireEvent.click(screen.getByRole('button', { name: '一键运行' }))

    await waitFor(() => expect(toast.error).toHaveBeenCalledWith('运行被阻塞：2 项未能执行'))
    expect(toast.success).not.toHaveBeenCalled()
  })

  it('有失败时同样走 error，不用 success 掩盖', async () => {
    mocks.startRun.mockResolvedValue(makeRun({ status: 'failed', passed: 0, failed: 2, total: 2 }))
    renderPage()
    await waitFor(() => expect(mocks.listRuns).toHaveBeenCalled())

    fireEvent.click(screen.getByRole('button', { name: '一键运行' }))

    await waitFor(() =>
      expect(toast.error).toHaveBeenCalledWith('运行完成：0 通过 / 2 失败'),
    )
    expect(toast.success).not.toHaveBeenCalled()
  })

  it('全部通过时才是 success', async () => {
    mocks.startRun.mockResolvedValue(makeRun({ status: 'done', passed: 3, failed: 0, total: 3 }))
    renderPage()
    await waitFor(() => expect(mocks.listRuns).toHaveBeenCalled())

    fireEvent.click(screen.getByRole('button', { name: '一键运行' }))

    await waitFor(() =>
      expect(toast.success).toHaveBeenCalledWith('运行完成：3 通过 / 0 失败'),
    )
    expect(toast.error).not.toHaveBeenCalled()
  })
})

describe('阻塞运行的可读性', () => {
  it('total 为 0 时覆盖显 —，运行状态显「阻断」', async () => {
    renderPage([
      makeRun({
        status: 'blocked',
        total: 0,
        passed: 0,
        failures: [
          { item_id: 0, title: '整体运行', kind: 'plan', evidence: '', message: '无可执行目标' },
        ],
      }),
    ])

    await waitFor(() => expect(screen.getByText('覆盖 —')).toBeTruthy())
    expect(screen.queryByText('覆盖 0/0')).toBeNull()
    expect(screen.getByText('阻断')).toBeTruthy()
    // 阻塞原因必须落到页面上，而不是只存在于一次性 toast 里
    expect(screen.getByText('方案无可执行项')).toBeTruthy()
    expect(screen.getByText('无可执行目标')).toBeTruthy()
    // evidence 为空时，这条失败项自身不得留下悬空的「· 证据」标签
    const failureCard = screen.getByText('方案无可执行项').closest('.rounded')
    expect(failureCard?.textContent).not.toContain('证据')
  })

  it('失败分类中文映射，且不再一律染红', async () => {
    renderPage([
      makeRun({
        status: 'blocked',
        total: 2,
        passed: 0,
        failed: 1,
        blocked: 1,
        failures: [
          { item_id: 1, title: '登录', kind: 'business', evidence: '/evidence/1/1', message: '断言失败' },
          { item_id: 2, title: '比分', kind: 'environment', evidence: '', message: '无可执行 URL' },
        ],
      }),
    ])

    await waitFor(() => expect(screen.getByText('业务失败')).toBeTruthy())
    expect(screen.getByText('环境阻塞')).toBeTruthy()
    expect(screen.queryByText('business')).toBeNull()
    expect(screen.queryByText('environment')).toBeNull()
    // 含 environment/plan 项时标题不得叫「失败分类」（阻塞不是质量问题）
    expect(screen.getByText('未通过 / 阻塞明细')).toBeTruthy()
    expect(screen.queryByText('失败分类')).toBeNull()
  })

  it('只有业务失败时标题保持「失败分类」', async () => {
    renderPage([
      makeRun({
        status: 'failed',
        total: 1,
        passed: 0,
        failed: 1,
        failures: [
          { item_id: 1, title: '登录', kind: 'business', evidence: '/evidence/1/1', message: '断言失败' },
        ],
      }),
    ])

    await waitFor(() => expect(screen.getByText('失败分类')).toBeTruthy())
    expect(screen.queryByText('未通过 / 阻塞明细')).toBeNull()
  })

  it('证据状态走 StatusBadge，跳过不再显示为失败色/裸英文', async () => {
    renderPage([
      makeRun({
        status: 'done',
        total: 2,
        passed: 1,
        skipped: 1,
        evidence: [
          { type: 'RESPONSE', ref: 'run:1:item:1', url: '/a', ts: '', status: 'pass' },
          { type: 'RESPONSE', ref: 'run:1:item:2', url: '/b', ts: '', status: 'skipped' },
        ],
      }),
    ])

    await waitFor(() => expect(screen.getByText('证据回放')).toBeTruthy())
    expect(screen.getByText('跳过')).toBeTruthy()
    expect(screen.queryByText('skipped')).toBeNull()
    expect(screen.queryByText('pass')).toBeNull()
  })
})
