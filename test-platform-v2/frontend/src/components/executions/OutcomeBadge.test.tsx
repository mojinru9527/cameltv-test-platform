// OutcomeBadge tests (v331-remediation-2 C3)
import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'

import OutcomeBadge from './OutcomeBadge'
import { OUTCOME_LABELS } from '@/api/executions'

describe('OutcomeBadge', () => {
  it('无 outcome 显示占位符（不猜测结论）', () => {
    render(<OutcomeBadge outcome={null} />)
    expect(screen.getByText('—')).toBeTruthy()
  })

  it('已知 outcome 渲染中文标签', () => {
    render(<OutcomeBadge outcome="BUSINESS_FAIL" />)
    expect(screen.getByText(OUTCOME_LABELS.BUSINESS_FAIL.label)).toBeTruthy()
  })

  it('未知 outcome 原样展示（颜色+文字双通道）', () => {
    render(<OutcomeBadge outcome="FUTURE_OUTCOME" />)
    expect(screen.getByText('FUTURE_OUTCOME')).toBeTruthy()
  })
})
