import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

vi.mock('./components/AssetTab', () => ({ default: () => <div>资产内容</div> }))
vi.mock('./components/DebugTab', () => ({ default: () => <div>调试内容</div> }))
vi.mock('./components/ApiCaseTab', () => ({ default: () => <div>用例内容</div> }))
vi.mock('./components/TaskTab', () => ({ default: () => <div>任务内容</div> }))
vi.mock('./components/ImportDialog', () => ({ default: () => null }))

import ApiTestPage from './index'

describe('API test page responsive navigation', () => {
  it('keeps narrow-screen tab scrolling inside the tab list', () => {
    render(<ApiTestPage />)

    const tabList = screen.getByRole('tablist')
    expect(tabList.className).toContain('max-w-full')
    expect(tabList.className).toContain('overflow-x-auto')
    expect(tabList.className).toContain('no-scrollbar')

    for (const tab of screen.getAllByRole('tab')) {
      expect(tab.className).toContain('flex-none')
    }
  })
})
