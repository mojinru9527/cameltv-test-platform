import { describe, expect, it } from 'vitest'
import { resolveApiBase } from './baseUrl'

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
