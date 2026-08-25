import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { afterEach, describe, expect, it, vi } from 'vitest'

const indexHtml = readFileSync(resolve(process.cwd(), 'index.html'), 'utf8')
const appMain = readFileSync(resolve(process.cwd(), 'src/main.tsx'), 'utf8')
const themeLabMain = readFileSync(resolve(process.cwd(), 'src/theme-lab/main.tsx'), 'utf8')

function getThemeBootstrapScript(): string {
  const match = indexHtml.match(/<script data-theme-bootstrap>([\s\S]*?)<\/script>/)
  if (!match) throw new Error('Theme bootstrap script is missing from index.html')
  return match[1]
}

function runThemeBootstrap({
  mode,
  colorTheme,
  prefersDark = false,
}: {
  mode?: string
  colorTheme?: string
  prefersDark?: boolean
}) {
  localStorage.clear()
  document.documentElement.className = ''
  delete document.documentElement.dataset.theme
  delete document.documentElement.dataset.themeId
  delete document.documentElement.dataset.uiTheme

  if (mode) localStorage.setItem('test-platform-theme-mode', mode)
  if (colorTheme) localStorage.setItem('test-platform-theme-color', colorTheme)

  vi.stubGlobal('matchMedia', vi.fn((query: string) => ({
    matches: query === '(prefers-color-scheme: dark)' ? prefersDark : false,
  })))

  window.Function(getThemeBootstrapScript())()
}

describe('initial theme paint', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    localStorage.clear()
    document.documentElement.className = ''
    delete document.documentElement.dataset.theme
    delete document.documentElement.dataset.themeId
    delete document.documentElement.dataset.uiTheme
  })

  it('applies dark-only Obsidian attributes before the React bundle loads', () => {
    runThemeBootstrap({ mode: 'light', colorTheme: 'obsidian-flow' })

    expect(document.documentElement.classList.contains('dark')).toBe(true)
    expect(document.documentElement.dataset.theme).toBe('obsidian-flow')
    expect(document.documentElement.dataset.themeId).toBe('obsidian-flow')
    expect(document.documentElement.dataset.uiTheme).toBe('obsidian-flow')
  })

  it('normalizes unknown persisted values without injecting attributes', () => {
    runThemeBootstrap({ mode: 'invalid-mode', colorTheme: 'unknown-theme', prefersDark: true })

    expect(document.documentElement.classList.contains('dark')).toBe(true)
    expect(document.documentElement.dataset.theme).toBe('obsidian-flow')
    expect(document.documentElement.dataset.themeId).toBe('obsidian-flow')
    expect(document.documentElement.dataset.uiTheme).toBe('obsidian-flow')
  })

  it('migrates an older saved color before first paint', () => {
    runThemeBootstrap({ mode: 'light', colorTheme: 'blue' })

    expect(document.documentElement.classList.contains('light')).toBe(true)
    expect(document.documentElement.dataset.theme).toBe('apple')
    expect(document.documentElement.dataset.themeId).toBe('apple')
    expect(document.documentElement.hasAttribute('data-ui-theme')).toBe(false)
  })
})

describe('Theme Lab stylesheet loading', () => {
  it('keeps Theme Lab CSS out of the production entry and in the lab entry', () => {
    expect(appMain).not.toContain("import './theme-lab/theme-lab.css'")
    expect(themeLabMain).toContain("import './theme-lab.css'")
  })
})
