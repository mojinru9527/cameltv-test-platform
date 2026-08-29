/** Safe JSON parse for backend fields that arrive as JSON-encoded strings. */
export function parseJson<T = Record<string, unknown>>(
  value: string | null | undefined,
  fallback: T | null = null as T | null,
): T | null {
  if (value === null || value === undefined) return fallback
  try {
    return JSON.parse(value) as T
  } catch {
    return fallback
  }
}

export function parseJsonArray<T = unknown>(value: string | null | undefined): T[] {
  if (!value) return []
  try {
    const parsed = JSON.parse(value)
    return Array.isArray(parsed) ? (parsed as T[]) : []
  } catch {
    return []
  }
}
