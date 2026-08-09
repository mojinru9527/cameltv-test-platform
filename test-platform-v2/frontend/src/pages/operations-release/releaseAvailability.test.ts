import { describe, expect, it } from 'vitest'

import { isReleaseControlUnavailable } from './releaseAvailability'

describe('release control availability', () => {
  it('classifies the expected unconfigured backend response', () => {
    expect(isReleaseControlUnavailable({
      message: 'release-control state store is not configured',
      response: { status: 503 },
    })).toBe(true)
  })

  it('does not hide unrelated server errors', () => {
    expect(isReleaseControlUnavailable({
      message: 'database timeout',
      response: { status: 500 },
    })).toBe(false)
  })
})
