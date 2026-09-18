import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import NodeStatusCard from '../NodeStatusCard'
import { NODE_STATUS_POLL_MS, type NodeStatus } from '@/api/executionJobs'

const mockState: {
  data: NodeStatus | undefined
  isLoading: boolean
  isError: boolean
  error: Error | null
} = { data: undefined, isLoading: false, isError: false, error: null }
const refetch = vi.fn()

vi.mock('@/hooks/useApi', () => ({
  useApi: () => ({
    data: mockState.data,
    isLoading: mockState.isLoading,
    isRefetching: false,
    isError: mockState.isError,
    error: mockState.error,
    refetch,
    setData: vi.fn(),
    abort: vi.fn(),
  }),
}))

const offline: NodeStatus = {
  online_nodes: 0,
  queue_length: 3,
  running_jobs: 0,
  stalled_jobs: 0,
  nodes: [],
}

const online: NodeStatus = {
  online_nodes: 2,
  queue_length: 1,
  running_jobs: 3,
  stalled_jobs: 1,
  nodes: [
    { node_id: 'tester-pc', status: 'online', capabilities: ['api', 'web'], last_health_at: null },
    { node_id: 'tester-pc-2', status: 'offline', capabilities: ['api'], last_health_at: null },
  ],
}

function renderCard() {
  return render(
    <MemoryRouter>
      <NodeStatusCard />
    </MemoryRouter>,
  )
}

beforeEach(() => {
  mockState.data = undefined
  mockState.isLoading = false
  mockState.isError = false
  mockState.error = null
  refetch.mockClear()
})

afterEach(() => {
  vi.useRealTimers()
})

describe('NodeStatusCard', () => {
  it('离线时给出明确提示与一键启动命令，而不是静默留白', () => {
    mockState.data = offline
    renderCard()
    expect(screen.getByTestId('node-offline')).toBeTruthy()
    expect(screen.getByText('本地节点未连接')).toBeTruthy()
    expect(screen.getByText('cameltv-node up --node-id my-pc')).toBeTruthy()
  })

  it('离线且有排队任务时说明任务不会被自动执行', () => {
    mockState.data = offline
    renderCard()
    expect(screen.getByText(/当前有 3 个任务在排队/)).toBeTruthy()
  })

  it('在线时显示节点数、队列与运行中，并列出节点能力', () => {
    mockState.data = online
    renderCard()
    expect(screen.getByTestId('node-online')).toBeTruthy()
    expect(screen.getByText('tester-pc')).toBeTruthy()
    expect(screen.getByText(/能力：api \/ web/)).toBeTruthy()
  })

  it('存在心跳超时任务时显式告警（不假装一切正常）', () => {
    mockState.data = online
    renderCard()
    expect(screen.getByText(/心跳已超时/)).toBeTruthy()
  })

  it('加载中显示骨架而不是先报「未连接」', () => {
    mockState.isLoading = true
    renderCard()
    expect(screen.queryByTestId('node-offline')).toBeNull()
    expect(screen.queryByText('本地节点未连接')).toBeNull()
  })

  it('拉取失败时显示错误并允许重试', async () => {
    mockState.isError = true
    mockState.error = new Error('boom')
    renderCard()
    expect(screen.getAllByText(/无法读取执行节点状态/).length).toBeGreaterThan(0)
    // ErrorState 的按钮带 aria-label="重新加载"，无障碍名称以 aria-label 为准
    const retry = screen.getByRole('button', { name: '重新加载' })
    fireEvent.click(retry)
    expect(refetch).toHaveBeenCalled()
  })

  it('字段缺失时降级为「未连接」而不是把首页搞崩', () => {
    mockState.data = { queue_length: 2 } as unknown as NodeStatus
    renderCard()
    expect(screen.getByTestId('node-offline')).toBeTruthy()
  })

  it('轮询间隔满足「节点上线后 10s 内刷新」的 DoD', () => {
    expect(NODE_STATUS_POLL_MS).toBeLessThanOrEqual(10_000)
  })

  it('按轮询间隔自动刷新', async () => {
    vi.useFakeTimers()
    mockState.data = offline
    renderCard()
    expect(refetch).not.toHaveBeenCalled()
    await vi.advanceTimersByTimeAsync(NODE_STATUS_POLL_MS)
    expect(refetch).toHaveBeenCalledTimes(1)
    await vi.advanceTimersByTimeAsync(NODE_STATUS_POLL_MS)
    expect(refetch).toHaveBeenCalledTimes(2)
  })

  it('卸载后停止轮询（useEffect cleanup）', async () => {
    vi.useFakeTimers()
    mockState.data = offline
    const { unmount } = renderCard()
    unmount()
    await vi.advanceTimersByTimeAsync(NODE_STATUS_POLL_MS * 3)
    expect(refetch).not.toHaveBeenCalled()
  })

  it('复制按钮把启动命令写入剪贴板', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined)
    Object.assign(navigator, { clipboard: { writeText } })
    mockState.data = offline
    renderCard()
    fireEvent.click(screen.getByRole('button', { name: /复制/ }))
    await waitFor(() => expect(writeText).toHaveBeenCalledWith('cameltv-node up --node-id my-pc'))
  })
})
