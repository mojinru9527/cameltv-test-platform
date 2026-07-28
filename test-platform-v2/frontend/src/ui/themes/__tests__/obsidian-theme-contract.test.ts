import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const obsidianCss = readFileSync(
  resolve(process.cwd(), 'src/ui/themes/obsidian-flow.css'),
  'utf8',
)
const semanticsCss = readFileSync(
  resolve(process.cwd(), 'src/ui/tokens/semantics.css'),
  'utf8',
)
const globalsCss = readFileSync(
  resolve(process.cwd(), 'src/globals.css'),
  'utf8',
)

describe('Obsidian theme contract', () => {
  it('uses data-theme as the only cascade selector', () => {
    expect(obsidianCss).toContain('[data-theme="obsidian-flow"]')
    expect(obsidianCss).not.toContain('[data-ui-theme="obsidian-flow"]')
    expect(globalsCss).not.toContain('[data-ui-theme="obsidian-flow"]')
    expect(globalsCss).not.toContain('.light[data-theme="obsidian-flow"]')
    expect(globalsCss).toContain('html.dark {\n  color-scheme: dark;')
    expect(globalsCss).toContain('html.light {\n  color-scheme: light;')
  })

  it('aliases shadcn variables through semantic tokens with readable muted text', () => {
    expect(obsidianCss).toContain('--color-canvas: var(--background);')
    expect(obsidianCss).toContain('--color-surface: var(--card);')
    expect(obsidianCss).toContain('--color-text: var(--foreground);')
    expect(obsidianCss).toContain('--color-text-secondary: var(--muted-foreground);')
    expect(obsidianCss).toContain('--color-action-primary: var(--primary);')
    expect(obsidianCss).toContain('--color-border-default: var(--border);')
    expect(obsidianCss).toContain('--color-focus-ring: var(--ring);')
    expect(obsidianCss).toContain('--color-hover: color-mix(in srgb, var(--primary) 12%, transparent);')
    expect(obsidianCss).toContain('--color-hover-text: var(--foreground);')
    expect(semanticsCss).toContain('--color-hover-text: var(--accent-foreground);')
    expect(globalsCss).toContain('--muted-foreground: #91a398;')
    expect(`${obsidianCss}\n${semanticsCss}\n${globalsCss}`).not.toContain('#718077')
  })

  it('keeps every compact button at least 44px for coarse pointers', () => {
    expect(obsidianCss).toMatch(
      /@media \(pointer: coarse\)[\s\S]*?\[data-theme="obsidian-flow"\] \.ui-btn-xs,[\s\S]*?\[data-theme="obsidian-flow"\] \.ui-btn-sm,[\s\S]*?\[data-theme="obsidian-flow"\] \.ui-btn-icon,[\s\S]*?\[data-theme="obsidian-flow"\] \.ui-btn-icon-sm,[\s\S]*?\[data-theme="obsidian-flow"\] \.ui-btn-icon-xs[\s\S]*?min-width: 44px;[\s\S]*?min-height: 44px;/,
    )
  })

  it('provides same-element reduced-transparency and unsupported-glass fallbacks', () => {
    expect(globalsCss).toContain(
      '[data-reduced-transparency="true"][data-theme="liquid-glass"] .glass-card',
    )
    expect(globalsCss).not.toContain(
      '[data-reduced-transparency="true"] [data-theme="liquid-glass"]',
    )
    expect(globalsCss).toMatch(/@supports not \(\(backdrop-filter: blur\(1px\)\)/)
    expect(globalsCss).toMatch(/@supports not[\s\S]*?-webkit-backdrop-filter: none;/)
  })
})
