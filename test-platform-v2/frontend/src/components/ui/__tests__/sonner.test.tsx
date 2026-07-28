import { act, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const themeState = vi.hoisted(() => ({
  mode: 'dark',
  colorTheme: 'cyberpunk',
}))

vi.mock('@/components/theme-provider', () => ({
  useTheme: () => themeState,
}))

vi.mock('sonner', () => ({
  Toaster: ({ theme }: { theme?: string }) => (
    <output data-testid="sonner-theme">{theme}</output>
  ),
}))

import { Toaster } from '../sonner'

describe('Toaster custom theme binding', () => {
  let systemDark = false
  let systemListeners: Set<() => void>

  beforeEach(() => {
    themeState.mode = 'dark'
    themeState.colorTheme = 'cyberpunk'
    systemDark = false
    systemListeners = new Set()
    vi.stubGlobal('matchMedia', vi.fn((query: string) => ({
      get matches() {
        return query === '(prefers-color-scheme: dark)' ? systemDark : false
      },
      media: query,
      onchange: null,
      addEventListener: (_event: string, listener: () => void) => systemListeners.add(listener),
      removeEventListener: (_event: string, listener: () => void) => systemListeners.delete(listener),
      addListener: vi.fn(),
      removeListener: vi.fn(),
      dispatchEvent: vi.fn(),
    })))
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('uses the repository light or dark mode instead of next-themes state', () => {
    const { rerender } = render(<Toaster />)
    expect(screen.getByTestId('sonner-theme').textContent).toBe('dark')

    themeState.mode = 'light'
    rerender(<Toaster />)

    expect(screen.getByTestId('sonner-theme').textContent).toBe('light')
  })

  it('tracks operating-system changes while repository mode is system', () => {
    themeState.mode = 'system'
    render(<Toaster />)
    expect(screen.getByTestId('sonner-theme').textContent).toBe('light')

    systemDark = true
    act(() => systemListeners.forEach((listener) => listener()))

    expect(screen.getByTestId('sonner-theme').textContent).toBe('dark')
  })
})
