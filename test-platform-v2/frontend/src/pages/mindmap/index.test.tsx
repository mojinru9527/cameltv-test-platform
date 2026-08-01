import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import MindmapPage from './index'

const markmapMocks = vi.hoisted(() => ({
  create: vi.fn(),
  setData: vi.fn(),
  fit: vi.fn(),
  destroy: vi.fn(),
  interrupt: vi.fn(),
  resolveSetData: undefined as undefined | (() => void),
}))

vi.mock('@/api/testcase', () => ({
  fetchDomains: vi.fn().mockResolvedValue([]),
  fetchTestCases: vi.fn(),
}))

vi.mock('@/hooks/useApi', () => ({
  default: () => ({
    data: {
      items: [{
        id: 1,
        domain: '接口',
        module: '登录',
        priority: 'P1',
        title: '登录成功',
      }],
    },
    isLoading: false,
    isError: false,
    error: null,
    refetch: vi.fn(),
  }),
}))

vi.mock('markmap-lib', () => ({
  Transformer: class {
    transform() {
      return { root: { content: '测试用例', children: [] } }
    }
  },
}))

vi.mock('markmap-view', () => ({
  Markmap: {
    create: markmapMocks.create,
  },
}))

describe('MindmapPage markmap lifecycle', () => {
  beforeEach(() => {
    markmapMocks.create.mockReset()
    markmapMocks.setData.mockReset()
    markmapMocks.fit.mockReset().mockResolvedValue(undefined)
    markmapMocks.destroy.mockReset()
    markmapMocks.interrupt.mockReset()

    markmapMocks.setData.mockImplementation(() => new Promise<void>((resolve) => {
      markmapMocks.resolveSetData = resolve
    }))
    markmapMocks.create.mockImplementation((_svg, _options, root) => {
      const instance = {
        setData: markmapMocks.setData,
        fit: markmapMocks.fit,
        destroy: markmapMocks.destroy,
        svg: { interrupt: markmapMocks.interrupt },
      }
      if (root) {
        void instance.setData(root).then(() => instance.fit())
      }
      return instance
    })
  })

  afterEach(() => {
    markmapMocks.resolveSetData = undefined
  })

  it('does not fit an async markmap after the page unmounts', async () => {
    const view = render(<MindmapPage />)

    await waitFor(() => expect(markmapMocks.create).toHaveBeenCalledTimes(1))
    view.unmount()

    await act(async () => {
      markmapMocks.resolveSetData?.()
      await Promise.resolve()
    })

    expect(markmapMocks.fit).not.toHaveBeenCalled()
    expect(markmapMocks.destroy).toHaveBeenCalledTimes(1)
  })

  it('keeps the exit control inside the fixed fullscreen card', async () => {
    render(<MindmapPage />)
    await act(async () => { await Promise.resolve() })

    fireEvent.click(screen.getByRole('button', { name: '全屏' }))

    const exitFullscreen = screen.getByRole('button', { name: '退出全屏' })
    const fullscreenCard = exitFullscreen.closest('[data-slot="card"]')
    expect(fullscreenCard).not.toBeNull()
    expect(fullscreenCard?.classList.contains('fixed')).toBe(true)
    expect(fullscreenCard?.classList.contains('z-50')).toBe(true)

    fireEvent.click(exitFullscreen)
    expect(screen.getByRole('button', { name: '全屏' })).not.toBeNull()
  })

  it('exits fullscreen with Escape', async () => {
    render(<MindmapPage />)
    fireEvent.click(screen.getByRole('button', { name: '全屏' }))
    expect(screen.getByRole('button', { name: '退出全屏' })).not.toBeNull()

    fireEvent.keyDown(window, { key: 'Escape' })

    expect(screen.getByRole('button', { name: '全屏' })).not.toBeNull()
  })
})
