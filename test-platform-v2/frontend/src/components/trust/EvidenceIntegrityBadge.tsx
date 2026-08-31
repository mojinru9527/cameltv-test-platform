import { Badge } from '@/ui'
import type { Evidence } from '@/api/executions'
import { formatBytes } from '@/components/executions/format'
import { deriveEvidenceIntegrity } from './evidenceIntegrity'

export interface EvidenceIntegrityBadgeProps {
  evidence?: Evidence | null
  className?: string
}

/**
 * Summarizes the integrity of a single evidence item:
 * Stored✓ / Sanitized✓ / Hash✓ / Size / Object✓.
 * Legacy 0-byte / hash-less placeholders are flagged as UNTRUSTED LEGACY EVIDENCE.
 */
export function EvidenceIntegrityBadge({ evidence, className }: EvidenceIntegrityBadgeProps) {
  const integrity = deriveEvidenceIntegrity(evidence)
  const mark = (ok: boolean) => (ok ? '✓' : '✗')

  return (
    <div className={`flex flex-wrap items-center gap-1.5 ${className ?? ''}`}>
      <Badge
        variant="outline"
        className={integrity.stored ? 'text-status-success' : 'text-status-danger'}
      >
        Stored {mark(integrity.stored)}
      </Badge>
      <Badge
        variant="outline"
        className={integrity.sanitized ? 'text-status-success' : 'text-status-danger'}
      >
        Sanitized {mark(integrity.sanitized)}
      </Badge>
      <Badge
        variant="outline"
        className={integrity.hash ? 'text-status-success' : 'text-status-danger'}
      >
        Hash {mark(integrity.hash)}
      </Badge>
      <Badge
        variant="outline"
        className={integrity.object ? 'text-status-success' : 'text-status-warning'}
      >
        Object {mark(integrity.object)}
      </Badge>
      <Badge
        variant="outline"
        className={integrity.sizeBytes > 0 ? '' : 'text-status-warning'}
      >
        Size {formatBytes(integrity.sizeBytes)}
      </Badge>
      {integrity.isLegacyUntrusted && (
        <Badge tone="danger">UNTRUSTED LEGACY EVIDENCE</Badge>
      )}
    </div>
  )
}
