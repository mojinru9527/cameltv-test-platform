import { describe, expect, it } from 'vitest'

import { formatTokenScopes } from './tokenScopes'

describe('token scope formatting', () => {
  it('renders structured scopes as readable Chinese punctuation', () => {
    expect(formatTokenScopes(['trigger', 'api'])).toBe('触发测试计划、开放 API')
  })

  it('keeps legacy Python-repr data readable during rollout', () => {
    expect(formatTokenScopes("['trigger', 'api']")).toBe('触发测试计划、开放 API')
  })

  it('renders the Worker registration scope as a user-facing label', () => {
    expect(formatTokenScopes(['workers:register'])).toBe('Worker 注册')
  })

  it('uses an explicit empty label', () => {
    expect(formatTokenScopes([])).toBe('无作用域')
  })
})
