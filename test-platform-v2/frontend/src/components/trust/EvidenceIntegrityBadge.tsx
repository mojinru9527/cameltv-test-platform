import { Badge } from '@/ui'
import { Check, X } from 'lucide-react'
import type { ReactNode } from 'react'
import type { Evidence } from '@/api/executions'
import { formatBytes } from '@/components/executions/format'
import { deriveEvidenceIntegrity } from './evidenceIntegrity'

export interface EvidenceIntegrityBadgeProps {
  evidence?: Evidence | null
  className?: string
}

/**
 * Summarizes the integrity of a single evidence item:
 * Stored / Sanitized / Hash / Size / Object, each marked with a Lucide icon.
 * Legacy 0-byte / hash-less placeholders are flagged as UNTRUSTED LEGACY EVIDENCE.
 */
export function EvidenceIntegrityBadge({ evidence, className }: EvidenceIntegrityBadgeProps) {
  const integrity = deriveEvidenceIntegrity(evidence)
  const mark = (ok: boolean): ReactNode =>
    ok ? <Check className="size-3" aria-label="通过" /> : <X className="size-3" aria-label="不通过" />

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
