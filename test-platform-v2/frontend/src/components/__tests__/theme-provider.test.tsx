import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ThemeProvider, useTheme } from '../theme-provider'
import type { ColorTheme } from '@/lib/themes'
import { UiThemeProvider, useUiTheme } from '@/ui/themes/UiThemeProvider'

function ThemeHarness() {
  const { mode, colorTheme, setMode, setColorTheme } = useTheme()
  return (
    <>
      <span data-testid="mode">{mode}</span>
      <button type="button" onClick={() => setColorTheme('liquid-glass' as ColorTheme)}>
        {colorTheme}
      </button>
      <button type="button" onClick={() => setColorTheme('obsidian-flow')}>
        切换到黑曜流界
      </button>
      <button type="button" onClick={() => setMode('light')}>
        请求浅色模式
      </button>
    </>
  )
}

function UiThemeHarness() {
  const { uiTheme, setUiTheme } = useUiTheme()
  return (
    <button type="button" onClick={() => setUiTheme('obsidian-flow')}>
      {uiTheme}
    </button>
  )
}

describe('ThemeProvider', () => {
  beforeEach(() => {
    localStorage.clear()
    document.documentElement.className = ''
    delete document.documentElement.dataset.theme
    delete document.documentElement.dataset.themeId
    delete document.documentElement.dataset.uiTheme
    Object.defineProperty(window, 'matchMedia', {
      configurable: true,
      value: vi.fn().mockImplementation((query: string) => ({
        matches: false,
        media: query,
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
      })),
    })
  })

  afterEach(() => {
    cleanup()
    vi.useRealTimers()
  })

  it('applies and persists an approved theme ID', async () => {
    localStorage.setItem('cameltv-theme-color', 'cyberpunk')
    render(<ThemeProvider><ThemeHarness /></ThemeProvider>)

    fireEvent.click(screen.getByRole('button', { name: 'cyberpunk' }))

    await waitFor(() => {
      expect(document.documentElement.dataset.themeId).toBe('liquid-glass')
    })
    expect(document.documentElement.dataset.theme).toBe('liquid-glass')
    expect(localStorage.getItem('cameltv-theme-color')).toBe('liquid-glass')
  })

  it('applies the complete dark-only root contract for Obsidian Flow', async () => {
    render(<ThemeProvider><ThemeHarness /></ThemeProvider>)

    fireEvent.click(screen.getByRole('button', { name: '切换到黑曜流界' }))

    await waitFor(() => {
      expect(document.documentElement.getAttribute('data-theme')).toBe('obsidian-flow')
    })
    expect(document.documentElement.getAttribute('data-theme-id')).toBe('obsidian-flow')
    expect(document.documentElement.getAttribute('data-ui-theme')).toBe('obsidian-flow')
    expect(document.documentElement.classList.contains('dark')).toBe(true)
    expect(screen.getByTestId('mode').textContent).toBe('dark')

    fireEvent.click(screen.getByRole('button', { name: '请求浅色模式' }))
    expect(document.documentElement.classList.contains('dark')).toBe(true)
    expect(screen.getByTestId('mode').textContent).toBe('dark')
  })

  it('derives the compatibility UI theme without independent storage', async () => {
    localStorage.setItem('cameltv-theme-color', 'cyberpunk')
    render(
      <ThemeProvider>
        <UiThemeProvider>
          <UiThemeHarness />
        </UiThemeProvider>
      </ThemeProvider>,
    )

    fireEvent.click(screen.getByRole('button', { name: 'default' }))

    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'obsidian-flow' })).toBeTruthy()
    })
    expect(document.documentElement.dataset.themeId).toBe('obsidian-flow')
    expect(localStorage.getItem('cameltv-theme-color')).toBe('obsidian-flow')
    expect(localStorage.getItem('cameltv-ui-theme')).toBeNull()
  })

  it('resolves an unsupported saved mode before applying Obsidian Flow', async () => {
    localStorage.setItem('cameltv-theme-color', 'obsidian-flow')
    localStorage.setItem('cameltv-theme-mode', 'light')
    render(<ThemeProvider><ThemeHarness /></ThemeProvider>)

    expect(screen.getByTestId('mode').textContent).toBe('dark')
    await waitFor(() => {
      expect(document.documentElement.classList.contains('dark')).toBe(true)
    })
    expect(document.documentElement.classList.contains('light')).toBe(false)
    expect(localStorage.getItem('cameltv-theme-mode')).toBe('dark')
  })

  it('clears an older transition timer before a newer theme transition', () => {
    vi.useFakeTimers()
    localStorage.setItem('cameltv-theme-color', 'cyberpunk')
    render(<ThemeProvider><ThemeHarness /></ThemeProvider>)

    act(() => vi.advanceTimersByTime(100))
    fireEvent.click(screen.getByRole('button', { name: '切换到黑曜流界' }))
    act(() => vi.advanceTimersByTime(150))

    expect(document.documentElement.classList.contains('theme-transition')).toBe(true)

    act(() => vi.advanceTimersByTime(100))
    expect(document.documentElement.classList.contains('theme-transition')).toBe(false)
  })

  it('restores a legacy saved theme through the migration map', async () => {
    localStorage.setItem('cameltv-theme-color', 'blue')
    render(<ThemeProvider><ThemeHarness /></ThemeProvider>)

    expect(screen.getByRole('button', { name: 'apple' })).toBeTruthy()
    await waitFor(() => {
      expect(document.documentElement.dataset.themeId).toBe('apple')
    })
    expect(localStorage.getItem('cameltv-theme-color')).toBe('apple')
  })
})
