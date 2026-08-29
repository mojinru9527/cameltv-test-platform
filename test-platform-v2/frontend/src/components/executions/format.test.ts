import { describe, it, expect } from 'vitest'
import { formatBytes, formatDuration } from './format'

describe('formatBytes', () => {
  it('formats bytes under 1KB', () => {
    expect(formatBytes(512)).toBe('512 B')
  })

  it('formats KB', () => {
    expect(formatBytes(2048)).toBe('2.0 KB')
  })

  it('formats MB', () => {
    expect(formatBytes(5 * 1024 * 1024)).toBe('5.0 MB')
  })

  it('returns placeholder for invalid input', () => {
    expect(formatBytes(-1)).toBe('—')
    expect(formatBytes(Number.NaN)).toBe('—')
  })
})

describe('formatDuration', () => {
  it('formats milliseconds below 1s', () => {
    expect(formatDuration(450)).toBe('450ms')
  })

  it('formats seconds', () => {
    expect(formatDuration(2500)).toBe('2.5s')
  })

  it('formats minutes and seconds', () => {
    expect(formatDuration(125000)).toBe('2m 5s')
  })

  it('returns placeholder for null/undefined', () => {
    expect(formatDuration(null)).toBe('—')
    expect(formatDuration(undefined)).toBe('—')
  })
})
