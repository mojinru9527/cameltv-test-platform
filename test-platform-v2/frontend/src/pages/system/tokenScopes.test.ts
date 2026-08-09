import { describe, expect, it } from 'vitest'

import { formatTokenScopes } from './tokenScopes'

describe('token scope formatting', () => {
  it('renders structured scopes as readable Chinese punctuation', () => {
    expect(formatTokenScopes(['trigger', 'api'])).toBe('trigger、api')
  })

  it('keeps legacy Python-repr data readable during rollout', () => {
    expect(formatTokenScopes("['trigger', 'api']")).toBe('trigger、api')
  })

  it('uses an explicit empty label', () => {
    expect(formatTokenScopes([])).toBe('无作用域')
  })
})
