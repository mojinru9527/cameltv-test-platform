import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ThemeProvider, useTheme } from '../theme-provider'
import type { ColorTheme } from '@/lib/themes'

function ThemeHarness() {
  const { colorTheme, setColorTheme } = useTheme()
  return (
    <button type="button" onClick={() => setColorTheme('liquid-glass' as ColorTheme)}>
      {colorTheme}
    </button>
  )
}

describe('ThemeProvider', () => {
  beforeEach(() => {
    localStorage.clear()
    document.documentElement.className = ''
    delete document.documentElement.dataset.theme
    delete document.documentElement.dataset.themeId
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

  afterEach(() => cleanup())

  it('applies and persists an approved theme ID', async () => {
    render(<ThemeProvider><ThemeHarness /></ThemeProvider>)

    fireEvent.click(screen.getByRole('button', { name: 'cyberpunk' }))

    await waitFor(() => {
      expect(document.documentElement.dataset.themeId).toBe('liquid-glass')
    })
    expect(document.documentElement.dataset.theme).toBe('liquid-glass')
    expect(localStorage.getItem('cameltv-theme-color')).toBe('liquid-glass')
  })

  it('restores a legacy saved theme through the migration map', async () => {
    localStorage.setItem('cameltv-theme-color', 'blue')
    render(<ThemeProvider><ThemeHarness /></ThemeProvider>)

    expect(screen.getByRole('button', { name: 'apple' })).toBeTruthy()
    await waitFor(() => {
      expect(document.documentElement.dataset.themeId).toBe('apple')
    })
  })
})
