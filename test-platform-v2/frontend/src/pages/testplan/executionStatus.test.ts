import { describe, expect, it } from 'vitest'

import { executionStatusLabel } from './executionStatus'

describe('executionStatusLabel', () => {
  it('localizes every supported execution status', () => {
    expect(['pass', 'fail', 'skip', 'block', 'pending'].map(executionStatusLabel)).toEqual([
      '通过', '失败', '跳过', '阻塞', '待执行',
    ])
  })

  it('keeps unknown states visible for forward compatibility', () => {
    expect(executionStatusLabel('queued')).toBe('未知状态（queued）')
    expect(executionStatusLabel(null)).toBe('-')
  })
})
