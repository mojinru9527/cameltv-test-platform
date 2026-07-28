import { describe, expect, it } from 'vitest'

import { COLOR_THEMES, DEFAULT_COLOR_THEME } from '@/lib/themes'
import {
  UI_THEMES,
  getDefaultUiTheme,
  getUiTheme,
} from '../registry'

describe('UI theme governance registry', () => {
  it('registers every canonical production theme exactly once', () => {
    const canonicalIds = COLOR_THEMES.map((theme) => theme.id)
    const registeredIds = UI_THEMES.map((theme) => theme.id)

    expect(registeredIds).toEqual(canonicalIds)
    expect(new Set(registeredIds).size).toBe(registeredIds.length)
  })

  it('keeps registry modes and CSS classes aligned with the canonical catalog', () => {
    for (const canonicalTheme of COLOR_THEMES) {
      const registeredTheme = getUiTheme(canonicalTheme.id)

      expect(registeredTheme).toBeDefined()
      expect(registeredTheme?.supportedModes).toEqual(canonicalTheme.supportedModes)
      expect(registeredTheme?.defaultMode).toBe(canonicalTheme.preferredMode)
      expect(registeredTheme?.cssClass).toBe(canonicalTheme.cssPreset)
      expect(registeredTheme?.fallbackThemeId).not.toBe(canonicalTheme.id)
    }
  })

  it('uses the canonical default instead of array position', () => {
    expect(getDefaultUiTheme().id).toBe(DEFAULT_COLOR_THEME)
  })
})
