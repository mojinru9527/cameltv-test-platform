import { describe, expect, it } from 'vitest'
import { resolveScenarioVersionId } from './mission'

describe('resolveScenarioVersionId', () => {
  it('returns the selected scenario current version id instead of the scenario id', () => {
    const scenarios = [
      {
        id: 7,
        scenario_version_id: 107,
        scenario_key: 'SC-7',
        title: '会员续费',
        priority: 'P0',
        risk_level: 'HIGH',
        review_status: 'APPROVED',
        version_no: 3,
        oracle_count: 2,
      },
    ]

    expect(resolveScenarioVersionId(scenarios, 7)).toBe(107)
    expect(resolveScenarioVersionId(scenarios, 107)).toBeNull()
  })
})
