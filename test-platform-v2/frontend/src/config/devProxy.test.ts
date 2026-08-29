import { describe, expect, it } from 'vitest'
import { API_V1_PROXY_PATTERN, API_V2_PROXY_PATTERN } from '../../config/devProxy'

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

describe('API v2 development proxy matcher', () => {
  const matcher = new RegExp(API_V2_PROXY_PATTERN)

  it.each([
    ['/api/v2', true],
    ['/api/v2/health', true],
    ['/api/v2/missions', true],
    ['/api/v20', false],
    ['/api/v1', false],
    ['/api', false],
    ['/missions', false],
  ])('matches %s = %s', (path, expected) => {
    expect(matcher.test(path)).toBe(expected)
  })
})
