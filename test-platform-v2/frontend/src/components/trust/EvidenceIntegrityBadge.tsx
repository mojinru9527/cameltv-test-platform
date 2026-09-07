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
 * Summarizes whether an evidence object is stored, sanitized, hashed and readable.
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
        已存储 {mark(integrity.stored)}
      </Badge>
      <Badge
        variant="outline"
        className={integrity.sanitized ? 'text-status-success' : 'text-status-danger'}
      >
        已脱敏 {mark(integrity.sanitized)}
      </Badge>
      <Badge
        variant="outline"
        className={integrity.hash ? 'text-status-success' : 'text-status-danger'}
      >
        校验值 {mark(integrity.hash)}
      </Badge>
      <Badge
        variant="outline"
        className={integrity.object ? 'text-status-success' : 'text-status-warning'}
      >
        文件可用 {mark(integrity.object)}
      </Badge>
      <Badge
        variant="outline"
        className={integrity.sizeBytes > 0 ? '' : 'text-status-warning'}
      >
        大小 {formatBytes(integrity.sizeBytes)}
      </Badge>
      {integrity.isLegacyUntrusted && (
        <Badge tone="danger">旧证据不可信</Badge>
      )}
    </div>
  )
}
