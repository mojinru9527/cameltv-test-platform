import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import ChartFrame from '../ChartFrame'

describe('ChartFrame accessibility contract', () => {
  it('pairs every visual chart with a summary and structured data table', () => {
    render(
      <ChartFrame
        title="通过率趋势"
        summary="最近两次执行的通过率从 80% 上升至 90%。"
        data={[{ period: '本周', rate: 90 }]}
        columns={[
          { key: 'period', label: '周期' },
          { key: 'rate', label: '通过率', format: (value) => `${value}%` },
        ]}
      >
        <div data-testid="visual-chart" />
      </ChartFrame>,
    )

    expect(screen.getByRole('figure', { name: '通过率趋势' })).toBeTruthy()
    expect(screen.getByText(/从 80% 上升至 90%/)).toBeTruthy()

    fireEvent.click(screen.getByText('查看图表数据'))
    expect(screen.getByRole('table', { name: '通过率趋势数据' })).toBeTruthy()
    expect(screen.getByRole('cell', { name: '90%' })).toBeTruthy()
  })
})
