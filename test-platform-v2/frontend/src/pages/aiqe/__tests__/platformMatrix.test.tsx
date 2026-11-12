import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const api = vi.hoisted(() => ({ getPlatformMatrix: vi.fn() }))
vi.mock('@/api/aiqeConsole', () => ({ getPlatformMatrix: api.getPlatformMatrix }))

const { default: PlatformMatrixPage } = await import('@/pages/aiqe/platform-matrix')

const MATRIX = {
  platforms: ['android', 'web'],
  capabilities: ['browser.chromium', 'device.android'],
  rows: [
    {
      capability: 'browser.chromium',
      cells: {
        android: { available: false, node_count: 0, nodes: [] },
        web: { available: true, node_count: 1, nodes: ['node-web-1'] },
      },
    },
    {
      capability: 'device.android',
      cells: {
        android: { available: false, node_count: 0, nodes: [] },
        web: { available: false, node_count: 0, nodes: [] },
      },
    },
  ],
  nodes: [
    {
      node_id: 'node-web-1',
      driver_key: 'playwright',
      driver_version: '1.50',
      platforms: ['web'],
      capabilities: ['browser.chromium'],
      available: true,
      last_evidence_ref: 'evidence://node-web-1',
      last_heartbeat_at: null,
    },
  ],
  available_nodes: 1,
}

function renderPage() {
  return render(
    <MemoryRouter>
      <PlatformMatrixPage />
    </MemoryRouter>,
  )
}

describe('平台矩阵页面（batch-339）', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('渲染真实节点能力矩阵与覆盖计数', async () => {
    api.getPlatformMatrix.mockResolvedValue(MATRIX)

    renderPage()

    expect(await screen.findByText('browser.chromium')).toBeTruthy()
    expect(screen.getByText('device.android')).toBeTruthy()
    expect(screen.getByText('✓ 1')).toBeTruthy()
    expect(screen.getByText('可用节点 1/1')).toBeTruthy()
    expect(screen.getByText('平台 2')).toBeTruthy()
    expect(screen.getByText('能力 2')).toBeTruthy()
  })

  it('无节点时显示空态', async () => {
    api.getPlatformMatrix.mockResolvedValue({
      platforms: [],
      capabilities: [],
      rows: [],
      nodes: [],
      available_nodes: 0,
    })

    renderPage()

    expect(await screen.findByText('暂无节点能力数据')).toBeTruthy()
  })
})
