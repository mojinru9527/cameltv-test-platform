/**
 * Shared trust / verification-provenance concept for the V3.9 "frontend Trust UX" layer.
 *
 * Levels rank how strongly a result's correctness has been verified. The backend does
 * not yet expose a single verification field, so consumers derive these defensively from
 * the data they already have (run origin, evidence integrity, oracle provenance).
 */

/** How strongly a result's correctness has been verified. */
export enum VerificationLevel {
  /** Verified by a unit-level check only (fastest, weakest). */
  UNIT_VERIFIED = 'UNIT_VERIFIED',
  /** Verified across an integration flow. */
  INTEGRATION_VERIFIED = 'INTEGRATION_VERIFIED',
  /** Verified against a staging / pre-production environment. */
  STAGING_VERIFIED = 'STAGING_VERIFIED',
  /** Verified against a real (non-prod) environment. */
  REAL_TEST_VERIFIED = 'REAL_TEST_VERIFIED',
  /** Verified read-only against production. */
  PROD_RO_VERIFIED = 'PROD_RO_VERIFIED',
  /** No positive verification has been recorded. */
  NOT_VERIFIED = 'NOT_VERIFIED',
  /** Imported / migrated from a legacy pipeline that cannot be re-verified. */
  LEGACY_UNVERIFIED = 'LEGACY_UNVERIFIED',
}

export const VERIFICATION_LEVEL_LABELS: Record<VerificationLevel, string> = {
  UNIT_VERIFIED: '单测验证',
  INTEGRATION_VERIFIED: '集成验证',
  STAGING_VERIFIED: '预发布验证',
  REAL_TEST_VERIFIED: '真实环境验证',
  PROD_RO_VERIFIED: '生产只读验证',
  NOT_VERIFIED: '未验证',
  LEGACY_UNVERIFIED: '旧版未验证',
}

/** Levels that represent a positively-verified trust state. */
const VERIFIED_LEVELS: ReadonlySet<VerificationLevel> = new Set<VerificationLevel>([
  VerificationLevel.UNIT_VERIFIED,
  VerificationLevel.INTEGRATION_VERIFIED,
  VerificationLevel.STAGING_VERIFIED,
  VerificationLevel.REAL_TEST_VERIFIED,
  VerificationLevel.PROD_RO_VERIFIED,
])

/** True when `level` represents a positively-verified trust state. */
export function isVerifiedLevel(level: VerificationLevel): boolean {
  return VERIFIED_LEVELS.has(level)
}

const VALID_LEVELS: ReadonlySet<string> = new Set<string>(Object.values(VerificationLevel))

/** Normalize any incoming value to a valid `VerificationLevel`, defaulting to NOT_VERIFIED. */
export function normalizeVerificationLevel(
  level: VerificationLevel | string | null | undefined,
): VerificationLevel {
  if (typeof level === 'string' && VALID_LEVELS.has(level)) {
    return level as VerificationLevel
  }
  return VerificationLevel.NOT_VERIFIED
}
