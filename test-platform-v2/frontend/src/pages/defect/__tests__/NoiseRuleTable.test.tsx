import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import NoiseRuleTable from '../NoiseRuleTable'

const future = new Date(Date.now() + 86400_000).toISOString()
const past = new Date(Date.now() - 86400_000).toISOString()

describe('NoiseRuleTable', () => {
  it('展示规则动作与到期状态', () => {
    render(
      <NoiseRuleTable
        rules={[
          { id: 1, pattern: '广告抖动', action: 'suppress', expires_at: future, status: 'active' },
          { id: 2, pattern: '旧规则', action: 'quarantine', expires_at: past, status: 'active' },
        ]}
      />
    )
    expect(screen.getByText('广告抖动')).toBeTruthy()
    expect(screen.getByText('抑制')).toBeTruthy()
    expect(screen.getByText('隔离')).toBeTruthy()
    expect(screen.getByText('生效中')).toBeTruthy()
    expect(screen.getByText('待复核')).toBeTruthy()
  })

  it('空态', () => {
    render(<NoiseRuleTable rules={[]} />)
    expect(screen.getByText('暂无噪音抑制规则')).toBeTruthy()
  })
})
