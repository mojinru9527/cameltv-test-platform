export interface RetryEntry {
  attempt: number
  status: string
  started_at?: string | null
  reason?: string
}

const STATUS_COLOR: Record<string, string> = {
  SUCCEEDED: 'bg-status-success-muted text-status-success',
  FAILED: 'bg-status-danger-muted text-status-danger',
  RETRYING: 'bg-status-warning-muted text-status-warning',
}

/** A compact list of a Run's retry attempts (V34-016 history visible). */
export function RetryHistory({ entries }: { entries: RetryEntry[] }) {
  if (!entries?.length) return <p className="text-sm text-muted-foreground">暂无重试记录</p>
  return (
    <ol className="space-y-2">
      {entries.map((e) => (
        <li key={e.attempt} className="flex items-center gap-2 text-sm">
          <span className="inline-flex size-5 items-center justify-center rounded-full bg-muted text-xs">{e.attempt}</span>
          <span className={`rounded px-1.5 py-0.5 text-xs ${STATUS_COLOR[e.status] ?? 'bg-muted text-muted-foreground'}`}>
            {e.status}
          </span>
          {e.reason && <span className="text-muted-foreground">{e.reason}</span>}
        </li>
      ))}
    </ol>
  )
}
