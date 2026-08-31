import { Badge, type BadgeTone } from '@/ui'
import {
  VerificationLevel,
  isVerifiedLevel,
  normalizeVerificationLevel,
} from './verificationLevel'
import {
  type RunTrust,
  deriveRunTrust,
} from './runTrust'

export interface TrustLevelBadgeProps {
  level?: VerificationLevel | string | null
  /** When true and no explicit level/assertions are given, the result is treated as legacy / unverified. */
  legacy?: boolean
  /** Run assertions used to derive trust (mirrors backend compute_run_trust). */
  assertions?: import('@/api/executions').Assertion[] | null
  className?: string
}

/** Resolve the effective verification level from an explicit level or a legacy flag. */
export function resolveTrustLevel(
  level?: VerificationLevel | string | null,
  legacy?: boolean,
): VerificationLevel {
  if (level != null && level !== '') return normalizeVerificationLevel(level)
  return legacy ? VerificationLevel.LEGACY_UNVERIFIED : VerificationLevel.UNIT_VERIFIED
}

/** Simplified two-state trust readout. */
export function TrustLevelBadge({ level, legacy, assertions, className }: TrustLevelBadgeProps) {
  let runTrust: RunTrust = 'LEGACY_UNVERIFIED'

  if (assertions != null) {
    // Prefer deriving from the run's assertions (mirrors compute_run_trust).
    runTrust = deriveRunTrust(assertions)
  } else {
    // Fall back to an explicit level / legacy flag.
    const resolved = resolveTrustLevel(level, legacy)
    runTrust = isVerifiedLevel(resolved) ? 'TRUSTED' : 'LEGACY_UNVERIFIED'
  }

  // TRUSTED -> VERIFIED. INVALID / LEGACY_UNVERIFIED are shown as LEGACY_UNVERIFIED.
  const [label, tone]: [string, BadgeTone] =
    runTrust === 'TRUSTED'
      ? ['Trust: VERIFIED', 'success']
      : ['Trust: LEGACY_UNVERIFIED', 'danger']

  return (
    <Badge tone={tone} className={className}>
      {label}
    </Badge>
  )
}
