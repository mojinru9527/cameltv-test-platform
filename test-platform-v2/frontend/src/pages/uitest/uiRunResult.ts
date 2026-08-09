export interface UiRunSummary {
  total: number
  passed: number
  failed: number
  skipped: number
  duration: number | null
}

function finiteNumber(value: unknown, fallback = 0): number {
  return typeof value === 'number' && Number.isFinite(value) ? value : fallback
}

export function parseUiRunResult(value: unknown): UiRunSummary | null {
  let payload = value
  if (typeof value === 'string') {
    try {
      payload = JSON.parse(value)
    } catch {
      return null
    }
  }
  if (!payload || typeof payload !== 'object' || !('total' in payload)) return null

  const result = payload as Record<string, unknown>
  return {
    total: finiteNumber(result.total),
    passed: finiteNumber(result.pass_ ?? result.passed),
    failed: finiteNumber(result.fail ?? result.failed),
    skipped: finiteNumber(result.skip ?? result.skipped),
    duration: typeof result.duration === 'number' && Number.isFinite(result.duration)
      ? result.duration
      : null,
  }
}
