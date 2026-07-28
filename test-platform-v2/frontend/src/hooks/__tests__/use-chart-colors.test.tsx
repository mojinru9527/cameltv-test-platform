import { act, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const themeState = vi.hoisted(() => ({
  colorTheme: 'cyberpunk',
  mode: 'dark',
}))

vi.mock('@/components/theme-provider', () => ({
  useTheme: () => themeState,
}))

import { useChartColors } from '../use-chart-colors'

function ChartColorProbe() {
  const colors = useChartColors()
  return <output data-testid="chart-color">{colors.chart1}</output>
}

describe('useChartColors theme updates', () => {
  let nextFrameId = 0
  let frames: Map<number, FrameRequestCallback>

  beforeEach(() => {
    themeState.colorTheme = 'cyberpunk'
    themeState.mode = 'dark'
    frames = new Map()
    document.documentElement.style.setProperty('--chart-1', '#112233')
    vi.stubGlobal('requestAnimationFrame', vi.fn((callback: FrameRequestCallback) => {
      const id = ++nextFrameId
      frames.set(id, callback)
      return id
    }))
    vi.stubGlobal('cancelAnimationFrame', vi.fn((id: number) => {
      frames.delete(id)
    }))
  })

  afterEach(() => {
    document.documentElement.removeAttribute('style')
    vi.unstubAllGlobals()
  })

  it('re-reads CSS chart variables when the custom theme changes', () => {
    const { rerender } = render(<ChartColorProbe />)

    expect(screen.getByTestId('chart-color').textContent).toBe('#112233')

    const initialFrame = [...frames.entries()].at(-1)
    expect(initialFrame).toBeTruthy()
    act(() => initialFrame?.[1](0))

    document.documentElement.style.setProperty('--chart-1', '#abcdef')
    themeState.colorTheme = 'apple'
    rerender(<ChartColorProbe />)

    const themeFrame = [...frames.entries()].at(-1)
    expect(themeFrame).toBeTruthy()
    act(() => themeFrame?.[1](16))

    expect(screen.getByTestId('chart-color').textContent).toBe('#abcdef')
  })

  it('cancels the pending color refresh when the consumer unmounts', () => {
    const { unmount } = render(<ChartColorProbe />)
    const frameId = [...frames.keys()].at(-1)

    unmount()

    expect(cancelAnimationFrame).toHaveBeenCalledWith(frameId)
  })
})
