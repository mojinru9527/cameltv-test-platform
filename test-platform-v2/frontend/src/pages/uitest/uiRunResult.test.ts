import { describe, expect, it } from 'vitest'

import { parseUiRunResult } from './uiRunResult'

describe('parseUiRunResult', () => {
  it('normalizes object and JSON-string summaries for business display', () => {
    expect(parseUiRunResult({ total: 10, pass_: 8, fail: 1, skip: 1, duration: 12.5 })).toEqual({
      total: 10,
      passed: 8,
      failed: 1,
      skipped: 1,
      duration: 12.5,
    })
    expect(parseUiRunResult('{"total":2,"pass_":2,"fail":0}')).toEqual({
      total: 2,
      passed: 2,
      failed: 0,
      skipped: 0,
      duration: null,
    })
  })

  it('returns null for non-summary payloads instead of inventing metrics', () => {
    expect(parseUiRunResult('runner disconnected')).toBeNull()
    expect(parseUiRunResult({ message: 'runner disconnected' })).toBeNull()
  })
})
