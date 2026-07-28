import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import DataTable, { type DataTableColumn } from '../DataTable'

interface Row {
  id: number
  name: string
}

const columns: DataTableColumn<Row>[] = [
  { key: 'name', header: '名称', sortable: true },
]

describe('DataTable keyboard accessibility', () => {
  it('always exposes a named, keyboard-focusable local scroll region', () => {
    render(
      <DataTable
        columns={columns}
        data={[{ id: 1, name: '计划 A' }]}
        rowKey={(row) => row.id}
        ariaLabel="测试计划数据"
      />,
    )

    const region = screen.getByRole('region', { name: '测试计划数据' })
    expect(region.getAttribute('tabindex')).toBe('0')
    expect(region.className).toContain('overflow-auto')
  })

  it('marks 50+ row datasets for contained rendering without dropping rows', () => {
    const rows = Array.from({ length: 100 }, (_, index) => ({
      id: index + 1,
      name: `计划 ${index + 1}`,
    }))

    render(
      <DataTable
        columns={columns}
        data={rows}
        rowKey={(row) => row.id}
      />,
    )

    expect(screen.getByRole('region', { name: '数据表格' }).getAttribute('data-density')).toBe(
      'high',
    )
    expect(screen.getAllByRole('row')).toHaveLength(101)
  })

  it('exposes sort state and uses a keyboard-operable sort control', () => {
    render(
      <DataTable
        columns={columns}
        data={[{ id: 1, name: '计划 A' }]}
        rowKey={(row) => row.id}
      />,
    )

    const header = screen.getByRole('columnheader', { name: /名称/ })
    const sortButton = screen.getByRole('button', { name: /名称/ })

    expect(header.getAttribute('aria-sort')).toBe('none')
    fireEvent.click(sortButton)
    expect(header.getAttribute('aria-sort')).toBe('ascending')
    fireEvent.click(sortButton)
    expect(header.getAttribute('aria-sort')).toBe('descending')
    fireEvent.click(sortButton)
    expect(header.getAttribute('aria-sort')).toBe('none')
  })

  it('opens clickable rows with Enter and Space', () => {
    const onRowClick = vi.fn()
    render(
      <DataTable
        columns={columns}
        data={[{ id: 1, name: '计划 A' }]}
        rowKey={(row) => row.id}
        onRowClick={onRowClick}
      />,
    )

    const row = screen.getByText('计划 A').closest('tr')
    expect(row?.getAttribute('role')).toBe('button')
    expect(row?.getAttribute('tabindex')).toBe('0')

    fireEvent.keyDown(row!, { key: 'Enter' })
    fireEvent.keyDown(row!, { key: ' ' })
    expect(onRowClick).toHaveBeenCalledTimes(2)
  })
})
