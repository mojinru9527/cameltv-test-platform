import { describe, expect, it } from 'vitest'
import { COLOR_THEMES, getThemeCssPreset, normalizeColorTheme } from '../themes'

describe('production theme registry', () => {
  it('exposes the five approved themes in comparison order', () => {
    expect(COLOR_THEMES.map((theme) => theme.id)).toEqual([
      'crystal',
      'xlab',
      'column',
      'clay',
      'liquid',
    ])
  })

  it('migrates legacy saved themes without losing project preferences', () => {
    expect(normalizeColorTheme('blue')).toBe('crystal')
    expect(normalizeColorTheme('dark-minimal')).toBe('xlab')
    expect(normalizeColorTheme('warm')).toBe('column')
    expect(normalizeColorTheme('nature')).toBe('clay')
    expect(normalizeColorTheme('unknown')).toBe('crystal')
  })

  it('maps approved IDs onto the existing CSS preset families', () => {
    expect(getThemeCssPreset('crystal')).toBe('blue')
    expect(getThemeCssPreset('xlab')).toBe('dark-minimal')
    expect(getThemeCssPreset('column')).toBe('warm')
    expect(getThemeCssPreset('clay')).toBe('nature')
    expect(getThemeCssPreset('liquid')).toBe('liquid')
  })
})
