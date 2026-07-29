import { describe, expect, it } from 'vitest'
import { API_V1_PROXY_PATTERN } from './devProxy'

describe('API v1 development proxy matcher', () => {
  const matcher = new RegExp(API_V1_PROXY_PATTERN)

  it.each([
    ['/api/v1', true],
    ['/api/v1/open/health', true],
    ['/api/v10', false],
    ['/api', false],
    ['/apitest', false],
    ['/api-keys', false],
  ])('matches %s = %s', (path, expected) => {
    expect(matcher.test(path)).toBe(expected)
  })
})
