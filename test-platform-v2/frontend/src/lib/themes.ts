export const COLOR_THEMES = [
  {
    id: 'crystal',
    number: '01',
    label: '晶穹',
    name: 'Crystal Command',
    description: 'Apple × Liquid Glass · 清晰日间协作',
    preview: ['#4768e8', '#f8fbff', '#182233'],
    cssPreset: 'blue',
    preferredMode: 'light',
  },
  {
    id: 'xlab',
    number: '02',
    label: '黑域',
    name: 'X-Lab',
    description: 'xAI × 轻赛博 · 夜间运行值守',
    preview: ['#4fe4ff', '#101315', '#edf2f4'],
    cssPreset: 'dark-minimal',
    preferredMode: 'dark',
  },
  {
    id: 'column',
    number: '03',
    label: '列阵',
    name: 'Column Pulse',
    description: 'ClickHouse · 高密度工业数据',
    preview: ['#f2c811', '#f7f7f4', '#171717'],
    cssPreset: 'warm',
    preferredMode: 'light',
  },
  {
    id: 'clay',
    number: '04',
    label: '软体',
    name: 'Clay Studio',
    description: '企业黏土拟态 · 低压力协作',
    preview: ['#7457cc', '#f3effa', '#332f3a'],
    cssPreset: 'nature',
    preferredMode: 'light',
  },
  {
    id: 'liquid',
    number: '05',
    label: '液境',
    name: 'Liquid Spectrum',
    description: '全景液态玻璃 · 丝滑连续操作',
    preview: ['#495edc', '#dce7f9', '#0c1731'],
    cssPreset: 'liquid',
    preferredMode: 'light',
  },
] as const

export type ColorTheme = (typeof COLOR_THEMES)[number]['id']
export type ThemeCssPreset = (typeof COLOR_THEMES)[number]['cssPreset']
export type ColorThemeDefinition = (typeof COLOR_THEMES)[number]

export const DEFAULT_COLOR_THEME: ColorTheme = 'crystal'

const THEME_BY_ID = new Map<ColorTheme, ColorThemeDefinition>(
  COLOR_THEMES.map((theme) => [theme.id, theme]),
)

const LEGACY_THEME_MAP: Record<string, ColorTheme> = {
  blue: 'crystal',
  'dark-minimal': 'xlab',
  warm: 'column',
  nature: 'clay',
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
