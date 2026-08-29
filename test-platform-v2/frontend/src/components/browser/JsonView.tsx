import { cn } from '@/lib/utils'

/** Narrow runtime check for a JSON object. */
export function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

/** Stable scalar/JSON stringification for display; never throws on bad input. */
export function formatValue(value: unknown): string {
  if (value === null || value === undefined) return '—'
  if (typeof value === 'string') return value
  if (typeof value === 'number' || typeof value === 'boolean') return String(value)
  try {
    return JSON.stringify(value)
  } catch {
    return '[无法序列化]'
  }
}

/** Pretty JSON for <pre> blocks. */
export function prettyJson(value: unknown): string {
  if (value === null || value === undefined) return '—'
  if (typeof value === 'string') return value
  try {
    return JSON.stringify(value, null, 2)
  } catch {
    return String(value)
  }
}

export interface JsonBlockProps {
  data: Record<string, unknown> | null | undefined
  /** Optional heading shown above the key/value rows. */
  label?: string
  className?: string
}

/**
 * Renders a flat business object as readable key/value rows. Nested objects /
 * arrays are collapsed into a pretty-printed JSON block so no info is hidden.
 * Live Service/Event/Cordis objects must never be passed here — only plain,
 * owned result data.
 */
export function JsonBlock({ data, label, className }: JsonBlockProps) {
  if (!data || Object.keys(data).length === 0) {
    return (
      <div className={cn('rounded-md border border-dashed px-3 py-3 text-center text-xs text-muted-foreground', className)}>
        {label ? `${label}：` : ''}无内容
      </div>
    )
  }

  return (
    <div className={cn('overflow-hidden rounded-md border', className)}>
      {label && (
        <div className="border-b bg-muted/50 px-3 py-1.5 text-xs font-medium text-muted-foreground">
          {label}
        </div>
      )}
      <dl className="divide-y divide-border text-sm">
        {Object.entries(data).map(([key, value]) => (
          <div key={key} className="grid grid-cols-[minmax(8rem,0.4fr)_1fr] gap-2 px-3 py-1.5">
            <dt className="truncate font-mono text-xs text-muted-foreground" title={key}>
              {key}
            </dt>
            <dd className="min-w-0 break-all">
              {isRecord(value) || Array.isArray(value) ? (
                <pre className="overflow-x-auto rounded bg-muted/50 p-1.5 font-mono text-[11px] leading-relaxed">
                  {formatValue(value)}
                </pre>
              ) : (
                <span className="break-all">{formatValue(value)}</span>
              )}
            </dd>
          </div>
        ))}
      </dl>
    </div>
  )
}
