import { describe, expect, it } from 'vitest'
import { getReportPassCount } from './index'

describe('getReportPassCount', () => {
  it('reads the pass field persisted in report snapshots', () => {
    expect(getReportPassCount({ total: 7, pass: 1, fail: 1 })).toBe(1)
  })

  it('keeps compatibility with the legacy pass_ field', () => {
    expect(getReportPassCount({ total: 7, pass_: 2 })).toBe(2)
  })
})
