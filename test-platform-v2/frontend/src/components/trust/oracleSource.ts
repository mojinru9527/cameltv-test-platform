import type { Assertion } from '@/api/executions'

/**
 * Oracle provenance. The backend does not expose a dedicated oracle-source field on the
 * Assertion payload, so we derive the source defensively from oracle_snapshot_json.
 */

export type OracleSource = 'TEST_ORACLE' | 'LEGACY_COMMAND_ASSERT' | 'LEGACY_EXECUTION' | 'UNKNOWN'

const PROVENANCE_KEYS = [
  'source_type',
  'oracle_type',
  'source',
  'provenance',
  'origin',
  'kind',
] as const

export interface OracleSourceMeta {
  label: string
  /** Short human hint about what the source means. */
  hint: string
}

export const ORACLE_SOURCE_META: Record<OracleSource, OracleSourceMeta> = {
  TEST_ORACLE: {
    label: '标准断言',
    hint: '单一权威来源的断言',
  },
  LEGACY_COMMAND_ASSERT: {
    label: '旧版命令断言',
    hint: '启发式命令断言',
  },
  LEGACY_EXECUTION: {
    label: '旧版执行结果',
    hint: '迁移的旧版执行结果',
  },
  UNKNOWN: {
    label: '来源未知',
    hint: '未识别出可信来源',
  },
}

/** Safely parse an `oracle_snapshot_json` value that may be a string or object. */
function parseSnapshot(value: unknown): Record<string, unknown> | null {
  if (value == null) return null
  if (typeof value === 'string') {
    if (!value.trim()) return null
    try {
      const parsed = JSON.parse(value)
      return typeof parsed === 'object' && parsed !== null
        ? (parsed as Record<string, unknown>)
        : null
    } catch {
      return null
    }
  }
  if (typeof value === 'object') return value as Record<string, unknown>
  return null
}

/** Read candidate provenance fields, preferring the top-level `oracle_source_type`. */
function readCandidates(assertion: Assertion | null | undefined): string[] {
  if (!assertion) return []
  const record = assertion as unknown as Record<string, unknown>
  const candidates: string[] = []

  // V3.9 — the API may serialize oracle_source_type at the top level now.
  const topSource = record.oracle_source_type
  if (typeof topSource === 'string' && topSource.trim()) {
    candidates.push(topSource.trim().toUpperCase())
  }

  const snap = parseSnapshot(record.oracle_snapshot_json)
  if (snap) {
    for (const key of PROVENANCE_KEYS) {
      const value = snap[key]
      if (typeof value === 'string' && value.trim()) candidates.push(value.trim().toUpperCase())
    }
  }
  return candidates
}

/** Derive the oracle source for an assertion, defaulting to UNKNOWN when not determined. */
export function deriveOracleSource(assertion: Assertion | null | undefined): OracleSource {
  for (const value of readCandidates(assertion)) {
    if (value.includes('LEGACY_EXECUTION') || value.includes('MIGRATED_EXECUTION')) {
      return 'LEGACY_EXECUTION'
    }
    if (
      value.includes('LEGACY') ||
      value.includes('COMMAND_ASSERT') ||
      value.includes('HEURISTIC') ||
      value.includes('GUESS')
    ) {
      return 'LEGACY_COMMAND_ASSERT'
    }
    if (
      value.includes('TEST_ORACLE') ||
      value.includes('CANONICAL') ||
      value.includes('SINGLE_SOURCE') ||
      value === 'TEST' ||
      value === 'ORACLE' ||
      value.includes('EXPECTED')
    ) {
      return 'TEST_ORACLE'
    }
  }
  return 'UNKNOWN'
}

const VALID_SOURCES: ReadonlySet<string> = new Set<string>([
  'TEST_ORACLE',
  'LEGACY_COMMAND_ASSERT',
  'LEGACY_EXECUTION',
  'UNKNOWN',
])

/** Normalize a raw source string to a valid `OracleSource`. */
export function normalizeOracleSource(source: string | null | undefined): OracleSource {
  if (typeof source === 'string' && source.trim()) {
    const upper = source.trim().toUpperCase()
    if (VALID_SOURCES.has(upper)) return upper as OracleSource
  }
  return 'UNKNOWN'
}
