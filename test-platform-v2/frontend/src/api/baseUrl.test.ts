import { describe, expect, it } from 'vitest'
import { resolveApiBase, resolveApiBaseFromEnv, resolveApiUrl } from './baseUrl'

describe('resolveApiBase', () => {
  it.each([
    [undefined, '/api/v1'],
    ['', '/api/v1'],
    ['   ', '/api/v1'],
    ['/api/v1', '/api/v1'],
    ['/gateway/api/v1/', '/gateway/api/v1'],
    ['http://localhost:8000/api/v1', 'http://localhost:8000/api/v1'],
    [' http://localhost:8000/api/v1/ ', 'http://localhost:8000/api/v1'],
  ])('resolves %j to %s', (value, expected) => {
    expect(resolveApiBase(value)).toBe(expected)
  })
})

describe('resolveApiBaseFromEnv', () => {
  it('prefers VITE_API_BASE_URL while keeping VITE_API_BASE compatible', () => {
    expect(resolveApiBaseFromEnv({
      VITE_API_BASE_URL: 'https://api.example.com/api/v1/',
      VITE_API_BASE: 'https://legacy.example.com/api/v1',
    })).toBe('https://api.example.com/api/v1')

    expect(resolveApiBaseFromEnv({
      VITE_API_BASE: 'https://legacy.example.com/api/v1',
    })).toBe('https://legacy.example.com/api/v1')
  })
})

describe('resolveApiUrl', () => {
  it('resolves API resources for proxy and direct deployments without duplicating the prefix', () => {
    expect(resolveApiUrl('/reports/9/export?format=pdf', '/api/v1'))
      .toBe('/api/v1/reports/9/export?format=pdf')
    expect(resolveApiUrl('/reports/9/export?format=pdf', 'https://api.example.com/api/v1'))
      .toBe('https://api.example.com/api/v1/reports/9/export?format=pdf')
  })
})
