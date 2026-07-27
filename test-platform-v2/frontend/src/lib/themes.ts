export const COLOR_THEMES = [
  {
    id: 'cyberpunk',
    number: '01',
    label: '赛博',
    name: 'Cyberpunk Terminal',
    description: '霓虹终端 × 暗黑数据工作台',
    preview: ['#00e5ff', '#090b0d', '#d0e0ed'],
    cssPreset: 'cyberpunk',
    preferredMode: 'dark',
  },
  {
    id: 'apple',
    number: '02',
    label: '晶穹',
    name: 'Apple Minimal',
    description: 'Apple 极简 × 日间协作',
    preview: ['#0071e3', '#f5f5f7', '#1d1d1f'],
    cssPreset: 'apple',
    preferredMode: 'light',
  },
  {
    id: 'clay',
    number: '03',
    label: '软体',
    name: 'Clay Studio',
    description: '黏土拟态 × 3D 触感交互',
    preview: ['#7457cc', '#efe9f7', '#332f3a'],
    cssPreset: 'clay',
    preferredMode: 'light',
  },
  {
    id: 'xlab',
    number: '04',
    label: '黑域',
    name: 'X-Lab',
    description: 'AI 实验室 × 夜间运行值守',
    preview: ['#4fe4ff', '#07090a', '#e2e8f0'],
    cssPreset: 'xlab',
    preferredMode: 'dark',
  },
  {
    id: 'liquid-glass',
    number: '05',
    label: '液境',
    name: 'Liquid Glass Panoramic',
    description: '全景液态玻璃 × 丝滑沉浸操作',
    preview: ['#7c5ce7', '#0a0a1a', '#e8e8f8'],
    cssPreset: 'liquid-glass',
    preferredMode: 'dark',
  },
] as const

export type ColorTheme = (typeof COLOR_THEMES)[number]['id']
export type ThemeCssPreset = (typeof COLOR_THEMES)[number]['cssPreset']
export type ColorThemeDefinition = (typeof COLOR_THEMES)[number]

export const DEFAULT_COLOR_THEME: ColorTheme = 'cyberpunk'

const THEME_BY_ID = new Map<ColorTheme, ColorThemeDefinition>(
  COLOR_THEMES.map((theme) => [theme.id, theme]),
)

const LEGACY_THEME_MAP: Record<string, ColorTheme> = {
  blue: 'apple',
  crystal: 'apple',
  'dark-minimal': 'xlab',
  warm: 'clay',
  column: 'clay',
  nature: 'clay',
  liquid: 'liquid-glass',
}

export function normalizeColorTheme(value: unknown): ColorTheme {
  if (typeof value !== 'string') return DEFAULT_COLOR_THEME
  if (THEME_BY_ID.has(value as ColorTheme)) return value as ColorTheme
  return LEGACY_THEME_MAP[value] ?? DEFAULT_COLOR_THEME
}

export function getThemeDefinition(theme: ColorTheme): ColorThemeDefinition {
  return THEME_BY_ID.get(theme) ?? THEME_BY_ID.get(DEFAULT_COLOR_THEME)!
}

export function getThemeCssPreset(theme: ColorTheme): ThemeCssPreset {
  return getThemeDefinition(theme).cssPreset
}
