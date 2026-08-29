import { Badge } from '@/ui'
import { EVIDENCE_TYPE_LABELS } from '@/api/executions'
import type { Evidence } from '@/api/executions'
import { formatBytes } from './format'

export default function ReplayEvidenceViewer({ evidence }: { evidence: Evidence | null }) {
  if (!evidence) {
    return (
      <p className="py-8 text-center text-sm text-muted-foreground">
        从证据列表选择一条查看详情。
      </p>
    )
  }

  const isHttp = /^https?:\/\//i.test(evidence.storage_uri)

  return (
    <div className="space-y-3 text-sm">
      <div className="flex flex-wrap items-center gap-2">
        <Badge variant="secondary">
          {EVIDENCE_TYPE_LABELS[evidence.evidence_type] ?? evidence.evidence_type}
        </Badge>
        <span className="font-mono text-xs text-muted-foreground">
          {evidence.content_hash.slice(0, 12)}…
        </span>
      </div>

      <dl className="space-y-1.5">
        <div className="flex justify-between gap-2">
          <dt className="text-muted-foreground">存储</dt>
          <dd>{evidence.storage_provider}</dd>
        </div>
        <div className="flex justify-between gap-2">
          <dt className="text-muted-foreground">内容类型</dt>
          <dd>{evidence.content_type}</dd>
        </div>
        <div className="flex justify-between gap-2">
          <dt className="text-muted-foreground">大小</dt>
          <dd>{formatBytes(evidence.size_bytes)}</dd>
        </div>
        <div className="flex justify-between gap-2">
          <dt className="text-muted-foreground">脱敏</dt>
          <dd>{evidence.sanitization_status}</dd>
        </div>
        <div className="flex justify-between gap-2">
          <dt className="text-muted-foreground">敏感度</dt>
          <dd>{evidence.sensitivity}</dd>
        </div>
      </dl>

      <p className="break-all rounded-lg border p-2 font-mono text-xs">{evidence.storage_uri}</p>

      {isHttp && (
        <a
          className="inline-flex items-center gap-1 text-primary"
          href={evidence.storage_uri}
          target="_blank"
          rel="noreferrer"
        >
          在新窗口打开
        </a>
      )}
    </div>
  )
}
