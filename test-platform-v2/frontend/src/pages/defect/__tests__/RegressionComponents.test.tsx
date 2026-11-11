import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import RunComparison, { type RunDiff } from '../RunComparison'
import RegressionDialog from '../RegressionDialog'

const diff: RunDiff = {
  fixed: ['AC1'],
  regressed: ['AC2'],
  still_failing: ['AC3'],
  new_assertions: ['AC4'],
  total_previous: 3,
  total_current: 4,
}

describe('RunComparison', () => {
  it('展示修复/回归/仍失败/新增', () => {
    render(<RunComparison diff={diff} />)
    expect(screen.getByText('Run 对比（旧 3 条 → 新 4 条）')).toBeTruthy()
    expect(screen.getByText('已修复（1）')).toBeTruthy()
    expect(screen.getByText('回归失败（1）')).toBeTruthy()
    expect(screen.getByText('仍失败（1）')).toBeTruthy()
    expect(screen.getByText('新增断言（1）')).toBeTruthy()
    expect(screen.getByText('AC1')).toBeTruthy()
    expect(screen.getByText('AC2')).toBeTruthy()
  })

  it('无差异时显示空态', () => {
    render(
      <RunComparison
        diff={{ fixed: [], regressed: [], still_failing: [], new_assertions: [], total_previous: 1, total_current: 1 }}
      />
    )
    expect(screen.getByText('无差异')).toBeTruthy()
  })
})

describe('RegressionDialog', () => {
  it('提交至少 7 位 SHA', async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined)
    const onClose = vi.fn()
    render(<RegressionDialog open defectId={12} onClose={onClose} onSubmit={onSubmit} />)

    fireEvent.change(screen.getByLabelText('修复 commit SHA'), { target: { value: 'abc1234' } })
    fireEvent.click(screen.getByRole('button', { name: '发起回归' }))

    await waitFor(() => expect(onSubmit).toHaveBeenCalledWith('abc1234'))
  })

  it('过短 SHA 不提交', async () => {
    const onSubmit = vi.fn()
    render(<RegressionDialog open defectId={12} onClose={vi.fn()} onSubmit={onSubmit} />)

    fireEvent.change(screen.getByLabelText('修复 commit SHA'), { target: { value: 'abc' } })
    fireEvent.click(screen.getByRole('button', { name: '发起回归' }))

    expect(await screen.findByText('请输入至少 7 位的修复 commit SHA')).toBeTruthy()
    expect(onSubmit).not.toHaveBeenCalled()
  })
})
