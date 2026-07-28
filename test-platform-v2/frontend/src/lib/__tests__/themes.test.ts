import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'
import {
  COLOR_THEMES,
  DEFAULT_COLOR_THEME,
  LEGACY_THEME_ALIASES,
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

  it('declares a real visual mode contract for every production theme', () => {
    expect(
      Object.fromEntries(
        COLOR_THEMES.map((theme) => [theme.id, theme.supportedModes]),
      ),
    ).toEqual({
      cyberpunk: ['light', 'dark'],
      apple: ['light', 'dark'],
      clay: ['light', 'dark'],
      xlab: ['light', 'dark'],
      'liquid-glass': ['light', 'dark'],
      'obsidian-flow': ['dark'],
    })
  })

  it('migrates legacy saved themes without losing project preferences', () => {
    expect(LEGACY_THEME_ALIASES).toEqual({
      blue: 'apple',
      crystal: 'apple',
      'dark-minimal': 'xlab',
      warm: 'clay',
      column: 'clay',
      nature: 'clay',
      liquid: 'liquid-glass',
    })
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

  it('keeps the synchronous first-paint bootstrap aligned with the typed catalog', () => {
    const html = readFileSync(resolve(process.cwd(), 'index.html'), 'utf8')
    const defaultTheme = html.match(/const defaultTheme = '([^']+)'/)?.[1]
    const knownThemeBlock = html.match(/const knownThemes = new Set\(\[([\s\S]*?)\]\)/)?.[1] ?? ''
    const legacyThemeBlock = html.match(/const legacyThemes = new Map\(\[([\s\S]*?)\]\)/)?.[1] ?? ''
    const knownThemes = [...knownThemeBlock.matchAll(/'([^']+)'/g)].map((match) => match[1])
    const legacyThemes = Object.fromEntries(
      [...legacyThemeBlock.matchAll(/\['([^']+)', '([^']+)'\]/g)]
        .map((match) => [match[1], match[2]]),
    )

    expect(defaultTheme).toBe(DEFAULT_COLOR_THEME)
    expect(knownThemes).toEqual(COLOR_THEMES.map((theme) => theme.id))
    expect(legacyThemes).toEqual(LEGACY_THEME_ALIASES)
  })
})
