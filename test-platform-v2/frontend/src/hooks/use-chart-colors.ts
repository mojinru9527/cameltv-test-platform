import { useMemo } from 'react'

/**
 * Read CSS custom properties from :root for chart coloring.
 * Returns stable hex-like values derived from the theme's chart-1…chart-5,
 * plus semantic priority colors.
 *
 * The values are read once at call time via getComputedStyle so they match
 * the current theme.
 */
function readVar(name: string, fallback: string): string {
  if (typeof window === 'undefined') return fallback
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim() || fallback
}

export interface ChartColors {
  chart1: string
  chart2: string
  chart3: string
  chart4: string
  chart5: string
  /** Priority colors — mapped to chart palette */
  p0: string
  p1: string
  p2: string
  p3: string
  /** Semantic bar colors */
  barTotal: string
  barPass: string
  barFail: string
  /** Grid / axis line colors */
  gridColor: string
  labelLineColor: string
}

const FALLBACKS: ChartColors = {
  chart1: '#3b82f6',
  chart2: '#10b981',
  chart3: '#8b5cf6',
  chart4: '#f59e0b',
  chart5: '#06b6d4',
  p0: '#ef4444',
  p1: '#f97316',
  p2: '#3b82f6',
  p3: '#6b7280',
  barTotal: '#3b82f6',
  barPass: '#22c55e',
  barFail: '#ef4444',
  gridColor: '#e5e7eb',
  labelLineColor: '#9ca3af',
}

/**
 * Returns chart colors sourced from CSS custom properties (--chart-1…--chart-5)
 * and semantic overrides. Falls back to a reasonable default palette when
 * the variables are unavailable (SSR / tests).
 */
export function useChartColors(): ChartColors {
  return useMemo(() => {
    if (typeof window === 'undefined') return FALLBACKS

    const c1 = readVar('--chart-1', FALLBACKS.chart1)
    const c2 = readVar('--chart-2', FALLBACKS.chart2)
    const c3 = readVar('--chart-3', FALLBACKS.chart3)
    const c4 = readVar('--chart-4', FALLBACKS.chart4)
    const c5 = readVar('--chart-5', FALLBACKS.chart5)

    // Destructive color for P0 failures
    const destructive = readVar('--destructive', FALLBACKS.p0)

    return {
      chart1: c1,
      chart2: c2,
      chart3: c3,
      chart4: c4,
      chart5: c5,
      p0: destructive,
      p1: c4,
      p2: c1,
      p3: readVar('--muted-foreground', FALLBACKS.p3),
      barTotal: c1,
      barPass: c2,
      barFail: destructive,
      gridColor: readVar('--border', FALLBACKS.gridColor),
      labelLineColor: readVar('--muted-foreground', FALLBACKS.labelLineColor),
    }
  }, [])
}
