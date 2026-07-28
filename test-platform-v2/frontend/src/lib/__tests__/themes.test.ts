import { describe, expect, it } from 'vitest'
import {
  COLOR_THEMES,
  getThemeCssPreset,
  getThemeDefinition,
  normalizeColorTheme,
} from '../themes'

describe('production theme registry', () => {
  it('exposes the six approved themes in comparison order', () => {
    expect(COLOR_THEMES.map((theme) => theme.id)).toEqual([
      'cyberpunk',
      'apple',
      'clay',
      'xlab',
      'liquid-glass',
      'obsidian-flow',
    ])
  })

  it('declares Obsidian Flow as a dark-only first-class theme', () => {
    expect(getThemeDefinition('obsidian-flow').supportedModes).toEqual(['dark'])
    expect(getThemeDefinition('obsidian-flow').preferredMode).toBe('dark')
  })

  it('migrates legacy saved themes without losing project preferences', () => {
    expect(normalizeColorTheme('blue')).toBe('apple')
    expect(normalizeColorTheme('crystal')).toBe('apple')
    expect(normalizeColorTheme('dark-minimal')).toBe('xlab')
    expect(normalizeColorTheme('warm')).toBe('clay')
    expect(normalizeColorTheme('column')).toBe('clay')
    expect(normalizeColorTheme('nature')).toBe('clay')
    expect(normalizeColorTheme('liquid')).toBe('liquid-glass')
    expect(normalizeColorTheme('obsidian-flow')).toBe('obsidian-flow')
    expect(normalizeColorTheme('unknown')).toBe('obsidian-flow')
  })

  it('maps approved IDs onto the existing CSS preset families', () => {
    expect(getThemeCssPreset('cyberpunk')).toBe('cyberpunk')
    expect(getThemeCssPreset('apple')).toBe('apple')
    expect(getThemeCssPreset('clay')).toBe('clay')
    expect(getThemeCssPreset('xlab')).toBe('xlab')
    expect(getThemeCssPreset('liquid-glass')).toBe('liquid-glass')
    expect(getThemeCssPreset('obsidian-flow')).toBe('obsidian-flow')
  })
})
