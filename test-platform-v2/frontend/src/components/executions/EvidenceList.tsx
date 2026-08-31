import { Badge } from '@/ui'
import { EVIDENCE_TYPE_LABELS } from '@/api/executions'
import type { Evidence } from '@/api/executions'
import { formatBytes } from './format'
import { EvidenceIntegrityBadge } from '@/components/trust/EvidenceIntegrityBadge'

export default function EvidenceList({ evidence }: { evidence: Evidence[] }) {
  if (evidence.length === 0) {
    return <p className="py-6 text-center text-sm text-muted-foreground">暂无证据。</p>
  }
  return (
    <ul className="space-y-2">
      {evidence.map((e) => (
        <li key={e.id} className="rounded-lg border p-3">
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="secondary">{EVIDENCE_TYPE_LABELS[e.evidence_type] ?? e.evidence_type}</Badge>
            <span className="font-mono text-xs text-muted-foreground">
              {e.content_hash.slice(0, 12)}…
            </span>
          </div>
          <p className="mt-1 break-all font-mono text-xs text-muted-foreground">{e.storage_uri}</p>
          <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
            <span>{formatBytes(e.size_bytes)}</span>
            <span>· {e.storage_provider}</span>
            <span>· {e.content_type}</span>
            <Badge variant="outline">{e.sanitization_status}</Badge>
          </div>
          <div className="mt-2">
            <EvidenceIntegrityBadge evidence={e} />
          </div>
        </li>
      ))}
    </ul>
  )
}
