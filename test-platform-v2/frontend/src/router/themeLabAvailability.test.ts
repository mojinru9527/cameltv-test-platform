import { describe, expect, it } from 'vitest'

import { isThemeLabEnabled } from './themeLabAvailability'

describe('isThemeLabEnabled', () => {
  it('is available during local development', () => {
    expect(isThemeLabEnabled(true, undefined)).toBe(true)
  })

  it('is closed by default in production and requires an explicit flag', () => {
    expect(isThemeLabEnabled(false, undefined)).toBe(false)
    expect(isThemeLabEnabled(false, 'false')).toBe(false)
    expect(isThemeLabEnabled(false, 'true')).toBe(true)
  })
})
