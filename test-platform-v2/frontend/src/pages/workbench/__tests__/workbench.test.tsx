import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { describe, expect, it, vi } from 'vitest'

import Workbench from '../index'
import type { DashboardTodo } from '@/types'

vi.mock('@/hooks/useApi', () => ({
  useApi: () => ({
    data: mockData,
    isLoading: false,
    isRefetching: false,
    isError: false,
    error: null,
    refetch: vi.fn(),
    setData: vi.fn(),
    abort: vi.fn(),
  }),
}))

const mockData: DashboardTodo = {
  reviews: {
    count: 2,
    items: [
      { id: 'review-1', title: '登录需求', subtitle: 'func 用例 待审', link: '/requirement/1/review' },
      { id: 'review-2', title: '支付需求', subtitle: 'api 用例 待审', link: '/requirement/2/review' },
    ],
  },
  running: {
    count: 1,
    items: [{ id: 'task-run-1', title: 'generate 任务', subtitle: '进度 40%', link: '/report' }],
  },
  failures: {
    count: 2,
    items: [
      { id: 'defect-1', title: '登录失败', subtitle: '严重级 P1', link: '/defect/1' },
      { id: 'task-fail-1', title: 'extract 任务失败', subtitle: '超时', link: '/report' },
    ],
  },
  releases: {
    count: 1,
    items: [{ id: 'release-1', title: 'v16.0.0', subtitle: '16.0.0 / 8.0.0', link: '/release-bundles/1' }],
  },
}

describe('我的待办 /workbench 页面', () => {
  it('渲染四区（待审/在跑/失败/待放行）及条目与直达链接', () => {
    render(
      <MemoryRouter>
        <Workbench />
      </MemoryRouter>,
    )

    expect(screen.getByText('我的待办')).toBeTruthy()
    expect(screen.getByText('待审')).toBeTruthy()
    expect(screen.getByText('在跑')).toBeTruthy()
    expect(screen.getByText('失败 / 需关注')).toBeTruthy()
    expect(screen.getByText('待放行')).toBeTruthy()

    // 条目与直达链接
    expect(screen.getByText('登录需求')).toBeTruthy()
    expect(screen.getByText('v16.0.0')).toBeTruthy()
    expect(screen.getByRole('link', { name: /登录需求/ }).getAttribute('href')).toBe('/requirement/1/review')
    expect(screen.getByRole('link', { name: /v16.0.0/ }).getAttribute('href')).toBe('/release-bundles/1')
  })
})
