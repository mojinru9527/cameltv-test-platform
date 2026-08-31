import { Badge, type BadgeTone } from '@/ui'
import type { Assertion } from '@/api/executions'
import {
  type OracleSource,
  ORACLE_SOURCE_META,
  deriveOracleSource,
  normalizeOracleSource,
} from './oracleSource'

export interface OracleSourceBadgeProps {
  assertion?: Assertion | null
  /** Explicit source string; when provided it takes precedence over the assertion snapshot. */
  source?: string | null
  className?: string
}

function toneFor(source: OracleSource): BadgeTone {
  if (source === 'TEST_ORACLE') return 'success'
  if (source === 'LEGACY_COMMAND_ASSERT' || source === 'LEGACY_EXECUTION') return 'warning'
  return 'neutral'
}

/**
 * Badge distinguishing a canonical single-source oracle (TEST_ORACLE) from
 * legacy / heuristic guesses (LEGACY_COMMAND_ASSERT / LEGACY_EXECUTION).
 */
export function OracleSourceBadge({ assertion, source, className }: OracleSourceBadgeProps) {
  const resolved = source != null ? normalizeOracleSource(source) : deriveOracleSource(assertion)
  const meta = ORACLE_SOURCE_META[resolved]

  return (
    <Badge tone={toneFor(resolved)} className={className} title={meta.hint}>
      {resolved} · {meta.label}
    </Badge>
  )
}
