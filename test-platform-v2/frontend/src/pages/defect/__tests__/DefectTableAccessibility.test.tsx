import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import DefectTable from '../DefectTable'

vi.mock('@/api/defect', () => ({
  deleteDefect: vi.fn(),
}))

const defect = {
  id: 1,
  defect_id: 'B60-P1-021',
  title: '移动端缺陷表格横向滚动区域不可聚焦',
  severity: 'P1',
  status: 'open',
  assignee_name: '测试工程师',
  case_title: '体育平台移动端验收',
  created_at: '2026-08-01T00:00:00Z',
}

afterEach(cleanup)

describe('DefectTable 可访问性', () => {
  it('让横向滚动区域成为有名称的键盘焦点停靠点', () => {
    render(
      <DefectTable
        data={{ items: [defect], page: 1, page_size: 20, total: 1 }}
        isLoading={false}
        isError={false}
        error={null}
        onRetry={vi.fn()}
        page={1}
        onPageChange={vi.fn()}
        onDetail={vi.fn()}
        onEdit={vi.fn()}
        onDeleted={vi.fn()}
        canUpdate={false}
        canDelete={false}
      />,
    )

    const scrollRegion = screen.getByRole('region', { name: '缺陷列表，可横向滚动' })
    expect(scrollRegion.getAttribute('data-slot')).toBe('table-container')
    expect(scrollRegion.getAttribute('tabindex')).toBe('0')

    scrollRegion.focus()
    expect(document.activeElement).toBe(scrollRegion)
  })
})
