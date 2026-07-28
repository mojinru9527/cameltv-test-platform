/**
 * 主题注册表 — 主题清单、版本、能力和状态
 *
 * 所有主题必须在此注册后才能参与生产渲染。
 * ThemeDefinition 契约见 docs/superpowers/plans/2026-07-27-ui-theme-component-governance.md 第 4 节。
 */

import {
  COLOR_THEMES,
  DEFAULT_COLOR_THEME,
  type ColorTheme,
  type ThemeCssPreset,
} from '@/lib/themes'

export interface ThemeDefinition {
  id: ColorTheme
  version: `${number}.${number}.${number}`
  label: string
  labelZh: string
  status: 'experimental' | 'beta' | 'stable' | 'deprecated'
  supportedModes: ReadonlyArray<'light' | 'dark'>
  defaultMode: 'light' | 'dark'
  density: 'compact' | 'standard' | 'comfortable'
  topology: 'dashboard' | 'split-pane' | 'editorial' | 'spatial' | 'tactile'
  material: 'solid' | 'glass' | 'clay' | 'industrial'
  motionSignature: string
  interactionSignature: readonly string[]
  capabilities: ReadonlyArray<
    'spotlight' | 'spatial-chain' | 'fluid-transition' | 'tactile-press' | 'command-first'
  >
  fallbackThemeId: ColorTheme
  cssClass: ThemeCssPreset
}

const THEME_METADATA: Record<
  ColorTheme,
  Omit<ThemeDefinition, 'id' | 'label' | 'supportedModes' | 'defaultMode' | 'cssClass'>
> = {
  cyberpunk: {
    version: '1.0.0',
    labelZh: '赛博终端',
    status: 'stable',
    density: 'compact',
    topology: 'dashboard',
    material: 'industrial',
    motionSignature: 'terminal-scan',
    interactionSignature: ['terminal-focus', 'neon-feedback', 'command-first'],
    capabilities: ['command-first'],
    fallbackThemeId: 'xlab',
  },
  apple: {
    version: '1.0.0',
    labelZh: '晶穹极简',
    status: 'stable',
    density: 'standard',
    topology: 'editorial',
    material: 'solid',
    motionSignature: 'quiet-continuity',
    interactionSignature: ['segmented-navigation', 'quiet-feedback', 'direct-manipulation'],
    capabilities: ['fluid-transition'],
    fallbackThemeId: 'clay',
  },
  clay: {
    version: '1.0.0',
    labelZh: '软体工坊',
    status: 'stable',
    density: 'comfortable',
    topology: 'tactile',
    material: 'clay',
    motionSignature: 'tactile-spring',
    interactionSignature: ['tactile-press', 'soft-depth', 'direct-manipulation'],
    capabilities: ['tactile-press', 'fluid-transition'],
    fallbackThemeId: 'apple',
  },
  xlab: {
    version: '1.0.0',
    labelZh: '黑域实验室',
    status: 'stable',
    density: 'compact',
    topology: 'split-pane',
    material: 'industrial',
    motionSignature: 'instrument-response',
    interactionSignature: ['precision-focus', 'instrument-feedback', 'command-first'],
    capabilities: ['command-first'],
    fallbackThemeId: 'cyberpunk',
  },
  'liquid-glass': {
    version: '1.0.0',
    labelZh: '液境玻璃',
    status: 'stable',
    density: 'standard',
    topology: 'spatial',
    material: 'glass',
    motionSignature: 'fluid-refraction',
    interactionSignature: ['glass-depth', 'fluid-transition', 'direct-manipulation'],
    capabilities: ['fluid-transition', 'spotlight'],
    fallbackThemeId: 'apple',
  },
  'obsidian-flow': {
    version: '1.1.0',
    labelZh: '黑曜流界',
    status: 'stable',
    density: 'standard',
    topology: 'spatial',
    material: 'glass',
    motionSignature: 'structural-continuity',
    interactionSignature: ['spotlight-focus', 'spatial-chain', 'inspector-first', 'command-first'],
    capabilities: ['spotlight', 'spatial-chain', 'fluid-transition', 'command-first'],
    fallbackThemeId: 'xlab',
  },
}

export const UI_THEMES: readonly ThemeDefinition[] = COLOR_THEMES.map((theme) => ({
  id: theme.id,
  label: theme.name,
  supportedModes: theme.supportedModes,
  defaultMode: theme.preferredMode,
  cssClass: theme.cssPreset,
  ...THEME_METADATA[theme.id],
}))

const UI_THEME_BY_ID = new Map(UI_THEMES.map((theme) => [theme.id, theme]))

export function getUiTheme(id: ColorTheme): ThemeDefinition | undefined {
  return UI_THEME_BY_ID.get(id)
}

export function getDefaultUiTheme(): ThemeDefinition {
  return UI_THEME_BY_ID.get(DEFAULT_COLOR_THEME)!
}
