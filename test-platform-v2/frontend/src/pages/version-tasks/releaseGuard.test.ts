import { describe, expect, it } from 'vitest'
import { isPassVerdictAllowed } from './[taskId]'
import type { VersionTaskRun } from '@/api/versionTask'

function run(counts: Partial<VersionTaskRun>): VersionTaskRun {
  return {
    id: 1,
    task_id: 1,
    status: 'done',
    progress: 100,
    total: 1,
    passed: 1,
    failed: 0,
    skipped: 0,
    blocked: 0,
    evidence: [],
    failures: [],
    ...counts,
  }
}

describe('isPassVerdictAllowed', () => {
  it('allows pass only after at least one real successful check', () => {
    expect(isPassVerdictAllowed(run({ passed: 1 }))).toBe(true)
    expect(isPassVerdictAllowed(run({ passed: 0, total: 0 }))).toBe(false)
  })

  it('blocks pass when any check failed, skipped or was blocked', () => {
    expect(isPassVerdictAllowed(run({ failed: 1 }))).toBe(false)
    expect(isPassVerdictAllowed(run({ skipped: 1 }))).toBe(false)
    expect(isPassVerdictAllowed(run({ blocked: 1 }))).toBe(false)
  })
})
