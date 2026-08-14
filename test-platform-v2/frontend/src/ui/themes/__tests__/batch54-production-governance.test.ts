import { readFileSync, readdirSync } from 'node:fs'
import { extname, relative, resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const sourceRoot = resolve(process.cwd(), 'src')
const excludedDirectories = new Set(['__tests__', 'theme-lab'])
const rawColorAllowlist = new Set([
  // Theme swatches and data visualisations need stable categorical palettes; product surfaces also expose text/table data.
  'hooks/use-chart-colors.ts',
  'lib/themes.ts',
  'pages/knowledge/components/GraphTab.tsx',
  'pages/knowledge/components/SphereTab.tsx',
  'pages/perftest/index.tsx',
  // Batch 182（P3-09）：perftest 指标图抽到同目录 components，图表色板随组件迁移。
  'pages/perftest/components/PerfTrendChart.tsx',
  // Obsidian-only visual shells are intentionally isolated behind the theme adapter.
  'ui/components/MetricStrip.tsx',
  'ui/patterns/ObsidianListPage.tsx',
  'ui/patterns/ObsidianWorkbench.tsx',
])

function portableRelativePath(file: string): string {
  return relative(sourceRoot, file).replaceAll('\\', '/')
}

function collectProductionSources(directory = sourceRoot): string[] {
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const absolutePath = resolve(directory, entry.name)

    if (entry.isDirectory()) {
      return excludedDirectories.has(entry.name) ? [] : collectProductionSources(absolutePath)
    }

    return ['.ts', '.tsx'].includes(extname(entry.name)) ? [absolutePath] : []
  })
}

function findSourceMatches(pattern: RegExp): string[] {
  return collectProductionSources().flatMap((file) => {
    const source = readFileSync(file, 'utf8')
    const matches = [...source.matchAll(pattern)]

    return matches.map((match) => {
      const line = source.slice(0, match.index).split('\n').length
      return `${portableRelativePath(file)}:${line} ${match[0]}`
    })
  })
}

function formatDebt(title: string, matches: string[]): string {
  const preview = matches.slice(0, 20).join('\n')
  const remainder = matches.length > 20 ? `\n...以及另外 ${matches.length - 20} 处` : ''
  return `${title}（共 ${matches.length} 处）\n${preview}${remainder}`
}

function collectProductionStyles(): string[] {
  return [
    resolve(sourceRoot, 'globals.css'),
    resolve(sourceRoot, 'theme-lab/theme-lab.css'),
    ...readdirSync(resolve(sourceRoot, 'ui/themes'))
      .filter((name) => name.endsWith('.css'))
      .map((name) => resolve(sourceRoot, 'ui/themes', name)),
  ]
}

describe('Batch 54 production UI governance', () => {
  it('does not collapse canonical themes through the legacy UI theme adapter', () => {
    const adapter = readFileSync(
      resolve(sourceRoot, 'ui/themes/UiThemeProvider.tsx'),
      'utf8',
    )

    expect(adapter).not.toMatch(
      /export type UiThemeId\s*=\s*['"]default['"]\s*\|\s*['"]obsidian-flow['"]/,
    )
    expect(adapter).not.toMatch(
      /colorTheme\s*===\s*['"]obsidian-flow['"]\s*\?\s*['"]obsidian-flow['"]\s*:\s*['"]default['"]/,
    )
    expect(adapter).not.toMatch(
      /theme\s*===\s*['"]obsidian-flow['"]\s*\?\s*['"]obsidian-flow['"]\s*:\s*['"]cyberpunk['"]/,
    )
  })

  it('uses semantic status and data tokens instead of fixed Tailwind palettes', () => {
    const fixedPaletteClasses = findSourceMatches(
      /\b(?:bg|text|border|ring|fill|stroke|from|via|to)-(?:red|rose|orange|amber|yellow|lime|green|emerald|teal|cyan|sky|blue|indigo|violet|purple|pink)-(?:50|100|200|300|400|500|600|700|800|900|950)\b/g,
    )

    expect(
      fixedPaletteClasses,
      formatDebt('业务 TSX 仍含固定色板类，应迁移到语义 tone/token', fixedPaletteClasses),
    ).toEqual([])
  })

  it('does not bypass theme surfaces with fixed grayscale utility classes', () => {
    const fixedGrayscaleClasses = findSourceMatches(
      /\b(?:bg|text|border|ring|fill|stroke|from|via|to)-(?:white|black|gray|slate)(?:\/[0-9]+|-(?:50|100|200|300|400|500|600|700|800|900|950))?\b/g,
    )

    expect(
      fixedGrayscaleClasses,
      formatDebt('业务 TSX 仍含固定明暗表面，应迁移到主题语义 token', fixedGrayscaleClasses),
    ).toEqual([])
  })

  it('does not hard-code raw color literals in production TSX', () => {
    const rawColorLiterals = findSourceMatches(
      /(?:(?<!&)#[0-9a-fA-F]{3,8}\b|(?:rgb|hsl)a?\((?!var\())/g,
    ).filter((match) => {
      const file = match.slice(0, match.indexOf(':'))
      return !rawColorAllowlist.has(file)
    })

    expect(
      rawColorLiterals,
      formatDebt('业务 TSX 仍含原始色值，应改用主题语义变量', rawColorLiterals),
    ).toEqual([])
  })

  it('does not render 8–11px business text', () => {
    const tinyTextClasses = findSourceMatches(/\btext-\[(?:8|9|10|11)px\]\b/g)
    const tinyTextStyles = collectProductionStyles().flatMap((file) => {
      const source = readFileSync(file, 'utf8')
      return [...source.matchAll(/font-size:\s*(?:8|9|10|11)px/g)].map((match) => {
        const line = source.slice(0, match.index).split('\n').length
        return `${portableRelativePath(file)}:${line} ${match[0]}`
      })
    })
    const violations = [...tinyTextClasses, ...tinyTextStyles]

    expect(
      violations,
      formatDebt('业务正文或控件文字低于 12px', violations),
    ).toEqual([])
  })

  it('does not use transition-all in production components or theme styles', () => {
    const transitionAllClasses = findSourceMatches(/\btransition-all\b/g)
    const transitionAllStyles = collectProductionStyles().flatMap((file) => {
      const source = readFileSync(file, 'utf8')
      return [...source.matchAll(/\btransition\s*:\s*all\b/g)].map((match) => {
        const line = source.slice(0, match.index).split('\n').length
        return `${portableRelativePath(file)}:${line} ${match[0]}`
      })
    })
    const violations = [...transitionAllClasses, ...transitionAllStyles]

    expect(
      violations,
      formatDebt('动效必须显式限定 transform/opacity/color 等属性', violations),
    ).toEqual([])
  })

  it('does not use structural emoji or native confirm dialogs', () => {
    const structuralEmoji = findSourceMatches(/[\u2600-\u27BF\u{1F000}-\u{1FAFF}]/gu)
    const nativeConfirm = findSourceMatches(/\b(?:window\.)?confirm\s*\(/g)
    const violations = [...structuralEmoji, ...nativeConfirm]

    expect(
      violations,
      formatDebt('结构图标必须使用 Lucide，危险操作必须使用产品内确认对话框', violations),
    ).toEqual([])
  })

  it('does not use invalid Tailwind ring property names in CSS', () => {
    const violations = collectProductionStyles().flatMap((file) => {
      const source = readFileSync(file, 'utf8')
      return [...source.matchAll(/\b(?:ring-width|ring-color|ring-offset)\s*:/g)].map((match) => {
        const line = source.slice(0, match.index).split('\n').length
        return `${portableRelativePath(file)}:${line} ${match[0]}`
      })
    })

    expect(
      violations,
      formatDebt('CSS 必须使用 outline/box-shadow 等有效属性实现焦点环', violations),
    ).toEqual([])
  })
})
