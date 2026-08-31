import type { Assertion } from '@/api/executions'

/**
 * Frontend mirror of the backend `compute_run_trust` (outcome_classifier.py).
 *
 * The backend does NOT expose a dedicated trust field on the run payload itself,
 * so we derive the run-level trust from its assertions by matching on the JSON
 * field names the API serializes: `oracle_source_type` and `trust_status`. These
 * may appear either directly on the assertion object or inside its
 * `oracle_snapshot_json`, so we read defensively from both.
 */

export type RunTrust = 'TRUSTED' | 'LEGACY_UNVERIFIED' | 'INVALID'

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

/** Read a field from the assertion top-level, falling back to its snapshot. */
function readAssertionField(assertion: Assertion, field: string): string | undefined {
  const record = assertion as unknown as Record<string, unknown>
  const top = record[field]
  if (typeof top === 'string' && top.trim()) return top.trim().toUpperCase()
  const snapshot = parseSnapshot(record.oracle_snapshot_json)
  const inSnapshot = snapshot?.[field]
  if (typeof inSnapshot === 'string' && inSnapshot.trim()) {
    return inSnapshot.trim().toUpperCase()
  }
  return undefined
}

function trustStatus(assertion: Assertion): string | undefined {
  return readAssertionField(assertion, 'trust_status')
}

function oracleSourceType(assertion: Assertion): string | undefined {
  return readAssertionField(assertion, 'oracle_source_type')
}

/** TRUSTED — both real TestOracle bound and marked TRUSTED.
 *  LEGACY_UNVERIFIED — no assertions, or any non-canonical / legacy assertion.
 *  INVALID — any assertion references a non-existent / tampered oracle.
 */
export function deriveRunTrust(assertions: Assertion[] | null | undefined): RunTrust {
  if (!assertions || assertions.length === 0) return 'LEGACY_UNVERIFIED'

  for (const assertion of assertions) {
    if (trustStatus(assertion) === 'INVALID') return 'INVALID'
  }

  const allTrusted = assertions.every(
    (assertion) =>
      oracleSourceType(assertion) === 'TEST_ORACLE' && trustStatus(assertion) === 'TRUSTED',
  )
  return allTrusted ? 'TRUSTED' : 'LEGACY_UNVERIFIED'
}

/** Collapse the three-state run trust to the two-state display the Trust UX shows. */
export function deriveRunTrustDisplay(
  assertions: Assertion[] | null | undefined,
): 'VERIFIED' | 'NOT_VERIFIED' {
  return deriveRunTrust(assertions) === 'TRUSTED' ? 'VERIFIED' : 'NOT_VERIFIED'
}
