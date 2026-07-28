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
