import { act, render, waitFor } from '@testing-library/react'
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
})
