import { Badge, type BadgeTone } from '@/ui'
import {
  VerificationLevel,
  VERIFICATION_LEVEL_LABELS,
  isVerifiedLevel,
  normalizeVerificationLevel,
} from './verificationLevel'

export interface VerificationLevelBadgeProps {
  level?: VerificationLevel | string | null
  className?: string
}

function toneFor(level: VerificationLevel): BadgeTone {
  if (isVerifiedLevel(level)) return 'success'
  if (level === VerificationLevel.LEGACY_UNVERIFIED) return 'danger'
  return 'warning' // NOT_VERIFIED
}

/** Badge showing the verification provenance of a result. */
export function VerificationLevelBadge({ level, className }: VerificationLevelBadgeProps) {
  if (level == null) return null
  const resolved = normalizeVerificationLevel(level)
  return (
    <Badge tone={toneFor(resolved)} className={className}>
      {VERIFICATION_LEVEL_LABELS[resolved]}
    </Badge>
  )
}
