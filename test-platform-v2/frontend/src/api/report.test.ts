import { describe, expect, it } from 'vitest'
import { exportReportUrl } from './report'

describe('exportReportUrl', () => {
  it('uses the same-origin proxy API base', () => {
    expect(exportReportUrl(12, 'csv', '/api/v1'))
      .toBe('/api/v1/reports/12/export?format=csv')
  })

  it('uses the configured direct API origin', () => {
    expect(exportReportUrl(12, 'pdf', 'https://api.example.com/gateway/api/v1/'))
      .toBe('https://api.example.com/gateway/api/v1/reports/12/export?format=pdf')
  })
})
