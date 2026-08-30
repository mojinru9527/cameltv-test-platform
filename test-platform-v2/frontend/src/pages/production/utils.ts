import type { JourneyStep, XhrRef } from '@/api/production'

/** Parse a JSON-ish cell (string or already-parsed) into a plain object, null on failure/absence. */
export function parseMaybeObject(value: unknown): Record<string, unknown> | null {
  if (value === null || value === undefined) return null
  if (typeof value === 'string') {
    try {
      const parsed = JSON.parse(value) as unknown
      return parsed && typeof parsed === 'object' && !Array.isArray(parsed)
        ? (parsed as Record<string, unknown>)
        : null
    } catch {
      return null
    }
  }
  return typeof value === 'object' && !Array.isArray(value) ? (value as Record<string, unknown>) : null
}

/** Normalize a journey step's xhr_refs into an array of XhrRef entries. */
export function normalizeXhrRefs(value: JourneyStep['xhr_refs']): XhrRef[] {
  if (value === null || value === undefined) return []
  if (Array.isArray(value)) {
    return value as unknown as XhrRef[]
  }
  if (typeof value === 'string') {
    try {
      const parsed = JSON.parse(value) as unknown
      return Array.isArray(parsed) ? (parsed as unknown as XhrRef[]) : [parsed as XhrRef]
    } catch {
      return []
    }
  }
  // A single object — treat as a one-entry list unless it looks like a map of records.
  if (typeof value === 'object') {
    const obj = value as Record<string, unknown>
    if ('method' in obj || 'status' in obj || 'url' in obj) {
      return [obj as unknown as XhrRef]
    }
    // Map-like shape: { "0": {...}, "1": {...} } or { request: {...}, response: {...} }.
    const entries = Object.values(obj).filter((v) => typeof v === 'object' && v !== null)
    if (entries.length > 0) return entries as unknown as XhrRef[]
  }
  return []
}

/** Human-readable string for a redacted value, falling back to "-". */
export function displayValue(value: unknown): string {
  if (value === null || value === undefined) return '-'
  if (typeof value === 'string') return value.length ? value : '-'
  if (typeof value === 'object') {
    try {
      const str = JSON.stringify(value)
      return str && str.length > 160 ? `${str.slice(0, 157)}…` : str
    } catch {
      return String(value)
    }
  }
  return String(value)
}

/** Redacted header map for display; masks authentication-sensitive values. */
export function redactedHeaders(headers: Record<string, unknown> | string | null | undefined): Record<string, string> {
  const obj = parseMaybeObject(headers)
  if (!obj) return {}
  const SKIP = /^(authorization|cookie|set-cookie|proxy-authorization|x-api-key|api-key|x-auth-token)$/i
  const result: Record<string, string> = {}
  for (const [key, value] of Object.entries(obj)) {
    if (SKIP.test(key)) {
      result[key] = '•••redacted•••'
    } else {
      result[key] = displayValue(value)
    }
  }
  return result
}
