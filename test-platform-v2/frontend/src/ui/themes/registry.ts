/**
 * 主题注册表 — 主题清单、版本、能力和状态
 *
 * 所有主题必须在此注册后才能参与生产渲染。
 * ThemeDefinition 契约见 docs/superpowers/plans/2026-07-27-ui-theme-component-governance.md 第 4 节。
 */

export interface ThemeDefinition {
  id: string
  version: `${number}.${number}.${number}`
  label: string
  labelZh: string
  status: 'experimental' | 'beta' | 'stable' | 'deprecated'
  supportedModes: Array<'light' | 'dark'>
  defaultMode: 'light' | 'dark'
  density: 'compact' | 'standard' | 'comfortable'
  topology: 'dashboard' | 'split-pane' | 'editorial' | 'spatial' | 'tactile'
  material: 'solid' | 'glass' | 'clay' | 'industrial'
  motionSignature: string
  interactionSignature: string[]
  capabilities: Array<
    'spotlight' | 'spatial-chain' | 'fluid-transition' | 'tactile-press' | 'command-first'
  >
  fallbackThemeId: string
  cssClass: string
}

export const UI_THEMES: ThemeDefinition[] = [
  {
    id: 'obsidian-flow',
    version: '1.1.0',
    label: 'Obsidian Flow',
    labelZh: '黑曜流界',
    status: 'stable',
    supportedModes: ['dark'],
    defaultMode: 'dark',
    density: 'standard',
    topology: 'spatial',
    material: 'glass',
    motionSignature: 'structural-continuity',
    interactionSignature: ['spotlight-focus', 'spatial-chain', 'inspector-first', 'command-first'],
    capabilities: ['spotlight', 'spatial-chain', 'fluid-transition', 'command-first'],
    fallbackThemeId: 'xlab',
    cssClass: 'obsidian-flow',
  },
  // 后续迁移旧主题到这里
]

export function getUiTheme(id: string): ThemeDefinition | undefined {
  return UI_THEMES.find((t) => t.id === id)
}

export function getDefaultUiTheme(): ThemeDefinition {
  return UI_THEMES[0]
}
