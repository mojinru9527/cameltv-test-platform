import type { Evidence } from '@/api/executions'

/**
 * Defensive derivation of evidence integrity.
 *
 * The Evidence payload may carry a backend `integrity_status`
 * (VERIFIED / MISSING / CORRUPT / PENDING) plus `sanitization_status`. When
 * `integrity_status` is present we use it to decide Stored / Hash / Object;
 * when absent (or PENDING) we fall back to deriving from content_hash length,
 * size_bytes, sanitization_status and storage_uri. 0-byte / empty-hash evidence
 * is always flagged as UNTRUSTED LEGACY EVIDENCE unless positively VERIFIED.
 */

export interface EvidenceIntegrity {
  /** A non-empty storage URI (and provider, when present) exists. */
  stored: boolean
  /** sanitization_status is present and not a known "not yet sanitized" marker. */
  sanitized: boolean
  /** content_hash is present and (when integrity_status is known) verified. */
  hash: boolean
  /** The stored object plausibly exists (stored AND has bytes / VERIFIED). */
  object: boolean
  sizeBytes: number
  /** True when there is a recoverable content hash. */
  hasHash: boolean
  /** True for evidence that cannot be trusted (0 bytes or missing hash) — legacy placeholder. */
  isLegacyUntrusted: boolean
}

const UNSANITIZED_STATUSES: ReadonlySet<string> = new Set<string>([
  '',
  'PENDING',
  'REJECTED',
  'UNSANITIZED',
  'RAW',
  'NONE',
  'UNPROCESSED',
  'NOT_SANITIZED',
  'SKIPPED',
])

export function deriveEvidenceIntegrity(evidence: Evidence | null | undefined): EvidenceIntegrity {
  if (!evidence) {
    return {
      stored: false,
      sanitized: false,
      hash: false,
      object: false,
      sizeBytes: 0,
      hasHash: false,
      isLegacyUntrusted: true,
    }
  }

  const sizeBytes =
    Number.isFinite(evidence.size_bytes) && evidence.size_bytes >= 0 ? evidence.size_bytes : 0
  const hasHash = typeof evidence.content_hash === 'string' && evidence.content_hash.length > 0
  const sanitized = !UNSANITIZED_STATUSES.has(
    (evidence.sanitization_status ?? '').toUpperCase().trim(),
  )
  const integrityStatus = (evidence.integrity_status ?? '').toUpperCase().trim()

  // Default (fallback) derivation: storage_uri presence, hash presence, bytes > 0.
  let stored = Boolean(evidence.storage_uri)
  let hash = hasHash
  let object = stored && sizeBytes > 0

  // Explicit backend integrity_status is authoritative when present.
  if (integrityStatus === 'VERIFIED') {
    stored = true
    hash = hasHash
    object = true
  } else if (integrityStatus === 'MISSING') {
    hash = hasHash
    object = false
  } else if (integrityStatus === 'CORRUPT') {
    hash = false
    object = false
  }
  // PENDING / absent → keep the derived fallback.

  const isLegacyUntrusted = integrityStatus !== 'VERIFIED' && (!hasHash || sizeBytes <= 0)

  return { stored, sanitized, hash, object, sizeBytes, hasHash, isLegacyUntrusted }
}
