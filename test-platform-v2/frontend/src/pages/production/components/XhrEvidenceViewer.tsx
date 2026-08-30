import { useState } from 'react'
import { Badge } from '@/ui'
import type { XhrRef } from '@/api/production'
import { displayValue, redactedHeaders } from '../utils'
import { ChevronDown, ChevronRight, Globe } from '@/lib/icons'

interface XhrEvidenceViewerProps {
  xhrRefs: XhrRef[]
  /** Optionally pre-open all entries. */
  defaultOpen?: boolean
}

function statusTone(status?: number | string | null): string {
  if (status == null) return 'bg-muted text-muted-foreground'
  const code = Number(status)
  if (Number.isNaN(code)) return 'bg-status-info-muted text-status-info'
  if (code >= 500) return 'bg-status-danger-muted text-status-danger'
  if (code >= 400) return 'bg-status-warning-muted text-status-warning'
  if (code >= 200) return 'bg-status-success-muted text-status-success'
  return 'bg-status-info-muted text-status-info'
}

/** Render a single sanitized XHR reference (method / status / redacted headers / body). */
function XhrEntry({ entry, defaultOpen }: { entry: XhrRef; defaultOpen?: boolean }) {
  const [open, setOpen] = useState(Boolean(defaultOpen))
  const url = entry.url ?? entry.request_url
  const headers = redactedHeaders(entry.request_headers ?? entry.headers)
  const body = entry.request_body ?? entry.response_body ?? entry.body

  return (
    <div className="rounded-lg border bg-muted/30 p-2">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="flex w-full items-center gap-2 text-left"
      >
        {open ? <ChevronDown className="size-3.5 shrink-0" /> : <ChevronRight className="size-3.5 shrink-0" />}
        <Badge tone="neutral" className="font-mono">{entry.method ?? 'GET'}</Badge>
        <Badge tone="neutral" className={statusTone(entry.status)}>{displayValue(entry.status)}</Badge>
        <span className="min-w-0 flex-1 truncate font-mono text-xs text-muted-foreground">{url ?? '(无 url)'}</span>
      </button>
      {open && (
        <div className="mt-2 space-y-2 pl-5 text-xs">
          {Object.keys(headers).length > 0 && (
            <div>
              <p className="mb-1 font-medium text-muted-foreground">请求头（已脱敏）</p>
              <dl className="space-y-0.5">
                {Object.entries(headers).map(([key, value]) => (
                  <div key={key} className="flex gap-2">
                    <dt className="w-40 shrink-0 truncate font-mono text-muted-foreground">{key}</dt>
                    <dd className="min-w-0 break-all font-mono">{value}</dd>
                  </div>
                ))}
              </dl>
            </div>
          )}
          {body !== null && body !== undefined && (
            <div>
              <p className="mb-1 font-medium text-muted-foreground">Body</p>
              <pre className="max-h-48 overflow-auto rounded-md bg-background p-2 font-mono whitespace-pre-wrap break-all text-xs">
                {displayValue(body)}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

/**
 * Show a journey step's sanitized xhr_refs (method / status / redacted headers / body).
 */
export function XhrEvidenceViewer({ xhrRefs, defaultOpen = false }: XhrEvidenceViewerProps) {
  if (xhrRefs.length === 0) {
    return <p className="py-1 text-xs text-muted-foreground">无网络请求明细。</p>
  }
  return (
    <div className="space-y-1.5">
      <div className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
        <Globe className="size-3.5" /> 请求明细（{xhrRefs.length}）
      </div>
      {xhrRefs.map((entry, i) => (
        <XhrEntry key={`${entry.method ?? ''}-${entry.status ?? ''}-${i}`} entry={entry} defaultOpen={defaultOpen} />
      ))}
    </div>
  )
}
