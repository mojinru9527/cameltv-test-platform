import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import InteractionAnnotator from './InteractionAnnotator'

vi.mock('sonner', () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}))

const api = vi.hoisted(() => ({
  saveInteractions: vi.fn(),
}))

vi.mock('@/api/requirementModules', () => ({
  saveInteractions: (...args: unknown[]) => api.saveInteractions(...args),
}))

const SAVED_JSON = JSON.stringify([
  {
    id: 'saved-61',
    trigger: '点击赛事入口',
    source_element: '赛事入口',
    target_page: '赛事详情',
    interaction_type: 'navigation',
    x: 12,
    y: 18,
    width: 220,
    height: 64,
  },
])

function makePage() {
  return {
    id: 99,
    name: '赛事入口页',
    page_interactions: SAVED_JSON,
  } as never
}

describe('InteractionAnnotator 保存→重载→编辑闭环（B60-P1-008）', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.saveInteractions.mockResolvedValue({})
  })

  it('历史标注重载后仍可编辑并保存，真实坐标不被清空', async () => {
    const onOpenChange = vi.fn()
    const { rerender } = render(
      <InteractionAnnotator
        open
        onOpenChange={onOpenChange}
        page={makePage()}
        screenshotUrls={['data:image/png;base64,AAAA']}
        allPages={['赛事详情', '首页']}
      />,
    )

    expect(screen.getByText('标注列表 (1)')).toBeTruthy()
    expect(screen.getByText('→ 赛事详情')).toBeTruthy()

    // 模拟保存后重载：相同的持久化数据重新挂载
    rerender(
      <InteractionAnnotator
        open
        onOpenChange={onOpenChange}
        page={makePage()}
        screenshotUrls={['data:image/png;base64,AAAA']}
        allPages={['赛事详情', '首页']}
      />,
    )
    expect(screen.getByText('标注列表 (1)')).toBeTruthy()

    // 点击已保存区域进入编辑，修改触发元素
    fireEvent.click(screen.getByText('→ 赛事详情'))
    const sourceInput = screen.getByLabelText('触发元素')
    fireEvent.change(sourceInput, { target: { value: '首页搜索框' } })

    fireEvent.click(screen.getByRole('button', { name: '保存' }))

    await waitFor(() => expect(api.saveInteractions).toHaveBeenCalledTimes(1))
    expect(api.saveInteractions).toHaveBeenCalledWith(99, {
      interactions: [
        {
          id: 'saved-61',
          trigger: '点击赛事入口',
          target_page: '赛事详情',
          interaction_type: 'navigation',
          source_element: '首页搜索框',
          x: 12,
          y: 18,
          width: 220,
          height: 64,
        },
      ],
      merge: false,
    })
    expect(onOpenChange).toHaveBeenCalledWith(false)
  })
})
