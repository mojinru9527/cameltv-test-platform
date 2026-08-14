import { afterAll, beforeAll, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import { SearchableSelect } from '../searchable-select'

// cmdk 依赖 ResizeObserver / scrollIntoView（jsdom 未实现）
class MockResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
}
beforeAll(() => {
  ;(globalThis as any).ResizeObserver = MockResizeObserver
  Element.prototype.scrollIntoView = () => {}
})
afterAll(() => {
  delete (globalThis as any).ResizeObserver
  delete (Element.prototype as any).scrollIntoView
})

const options = [
  { value: '用户端/首页', label: '用户端/首页', group: '用户端' },
  { value: '用户端/直播', label: '用户端/直播', group: '用户端' },
  { value: '运营后台/内容管理', label: '运营后台/内容管理', group: '运营后台' },
  { value: '接口测试/首页', label: '接口测试/首页', group: '接口测试' },
  { value: 'UGC', label: 'UGC', group: '其他' },
]

describe('SearchableSelect（Batch 178 / FIX-173-P2-03）', () => {
  it('展示当前选中项标签', () => {
    render(
      <SearchableSelect value="UGC" onValueChange={() => {}} options={options} placeholder="选择域" />,
    )
    expect(screen.getByRole('combobox').textContent).toContain('UGC')
  })

  it('未选中时展示 placeholder', () => {
    render(<SearchableSelect value="" onValueChange={() => {}} options={options} placeholder="选择域" />)
    expect(screen.getByRole('combobox').textContent).toContain('选择域')
  })

  it('打开后按分组展示选项，选择触发 onValueChange', () => {
    const onChange = vi.fn()
    render(<SearchableSelect value="" onValueChange={onChange} options={options} placeholder="选择域" />)
    fireEvent.click(screen.getByRole('combobox'))
    // 分组标题可见
    expect(screen.getByText('用户端')).toBeTruthy()
    expect(screen.getByText('运营后台')).toBeTruthy()
    expect(screen.getByText('接口测试')).toBeTruthy()
    expect(screen.getByText('其他')).toBeTruthy()
    // 选择一项
    fireEvent.click(screen.getByText('UGC'))
    expect(onChange).toHaveBeenCalledWith('UGC')
  })

  it('输入关键字过滤选项（搜索 100+ 项域列表的核心能力）', () => {
    render(<SearchableSelect value="" onValueChange={() => {}} options={options} placeholder="选择域" />)
    fireEvent.click(screen.getByRole('combobox'))
    const input = screen.getByPlaceholderText('搜索选择域...')
    fireEvent.change(input, { target: { value: '直播' } })
    expect(screen.getByText('用户端/直播')).toBeTruthy()
    expect(screen.queryByText('用户端/首页')).toBeNull()
    expect(screen.queryByText('UGC')).toBeNull()
  })

  it('无匹配时展示空态文案', () => {
    render(<SearchableSelect value="" onValueChange={() => {}} options={options} placeholder="选择域" />)
    fireEvent.click(screen.getByRole('combobox'))
    const input = screen.getByPlaceholderText('搜索选择域...')
    fireEvent.change(input, { target: { value: '不存在的域xyz' } })
    expect(screen.getByText('无匹配选项')).toBeTruthy()
  })
})
