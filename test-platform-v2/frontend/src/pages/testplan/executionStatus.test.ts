import { describe, expect, it } from 'vitest'

import { execStatusLabel, normalizeExecStatus } from '@/utils/executionStatus'

describe('executionStatus 共享映射（Batch 182 / P1-06）', () => {
  it('localizes every canonical execution status', () => {
    expect(['pending', 'running', 'passed', 'failed', 'skipped', 'cancelled', 'blocked'].map(execStatusLabel)).toEqual([
      '待执行', '执行中', '通过', '失败', '跳过', '已取消', '阻塞',
    ])
  })

  it('localizes legacy values for historical data compatibility', () => {
    expect(['pass', 'fail', 'skip', 'block', 'done', 'idle'].map(execStatusLabel)).toEqual([
      '通过', '失败', '跳过', '阻塞', '通过', '待执行',
    ])
  })

  it('normalizes legacy values to the canonical vocabulary', () => {
    expect(['pass', 'fail', 'skip', 'block', 'done', 'idle', 'passed'].map(normalizeExecStatus)).toEqual([
      'passed', 'failed', 'skipped', 'blocked', 'passed', 'pending', 'passed',
    ])
  })

  it('keeps unknown states visible for forward compatibility', () => {
    expect(execStatusLabel('queued')).toBe('queued')
    expect(execStatusLabel(null)).toBe('')
  })
})
