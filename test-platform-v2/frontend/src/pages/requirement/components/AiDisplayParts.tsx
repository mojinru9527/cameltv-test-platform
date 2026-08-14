import { Badge } from '@/ui'
import { ArrowRight, Globe, Monitor, Pencil, Plus, Smartphone } from '@/lib/icons'

export const PRIORITY_CLASSES: Record<string, string> = {
  P0: 'border-status-danger-border bg-status-danger-muted text-status-danger',
  P1: 'border-status-warning-border bg-status-warning-muted text-status-warning',
  P2: 'border-status-info-border bg-status-info-muted text-status-info',
  P3: 'border-border bg-muted text-muted-foreground',
}

export const SEVERITY_CONFIG: Record<string, { color: string; label: string }> = {
  high: { color: 'var(--color-status-danger)', label: '高' },
  medium: { color: 'var(--color-status-warning)', label: '中' },
  low: { color: 'var(--color-status-info)', label: '低' },
}

export const SEVERITY_BADGE_CLASSES: Record<string, string> = {
  high: 'border-status-danger-border bg-status-danger-muted text-status-danger',
  medium: 'border-status-warning-border bg-status-warning-muted text-status-warning',
  low: 'border-status-info-border bg-status-info-muted text-status-info',
}

export const TYPE_LABELS: Record<string, string> = {
  functional: '功能',
  ui: '界面',
  data: '数据',
  integration: '集成',
}

// ── Client scope display helpers ──

export const CLIENT_SCOPE_CONFIG: Record<string, { icon: typeof Monitor; label: string; className: string }> = {
  app: { icon: Smartphone, label: 'App', className: 'border-status-success-border bg-status-success-muted text-status-success' },
  pc: { icon: Monitor, label: 'PC', className: 'border-status-info-border bg-status-info-muted text-status-info' },
  web: { icon: Globe, label: 'Web', className: 'border-status-accent-border bg-status-accent-muted text-status-accent' },
}

export function ClientScopeBadges({ clients }: { clients: string[] }) {
  if (!clients || clients.length === 0) return null
  return (
    <span className="inline-flex gap-0.5 ml-1 align-middle">
      {clients.map((c) => {
        const cfg = CLIENT_SCOPE_CONFIG[c]
        if (!cfg) return null
        const Icon = cfg.icon
        return (
          <Badge key={c} tone="neutral" className={`text-xs leading-[16px] px-1 gap-0.5 ${cfg.className}`} title={cfg.label + '端'}>
            <Icon className="size-3" />
            {cfg.label}
          </Badge>
        )
      })}
    </span>
  )
}

/** VersionMarkerBadge — shows version origin for function points (batch-28). */
export function VersionMarkerBadge({ fp, diffStatus, baseVersion }: {
  fp: { _inherited?: boolean; _from_version?: string }
  diffStatus?: string
  baseVersion?: string
}) {
  if (fp._inherited) {
    return (
      <Badge tone="neutral" className="text-xs text-status-info border-status-info-border">
        <ArrowRight className="size-3" />沿用自 {fp._from_version || baseVersion || '?'}
      </Badge>
    )
  }
  if (diffStatus === 'update') {
    return (
      <Badge tone="neutral" className="text-xs text-status-warning border-status-warning-border">
        <Pencil className="size-3" />本版本变更
      </Badge>
    )
  }
  return (
    <Badge tone="neutral" className="text-xs text-status-success border-status-success-border">
      <Plus className="size-3" />首次提取
    </Badge>
  )
}

export function renderSteps(steps: string) {
  try {
    const arr = JSON.parse(steps)
    if (!Array.isArray(arr) || arr.length === 0) return <span className="text-muted-foreground text-xs">-</span>
    return (
      <ol className="m-0 pl-[18px] max-w-[230px] break-words">
        {arr.map((s: any, i: number) => (
          <li key={i} className="text-xs leading-[18px] break-words">
            <span className="text-foreground">{s.desc}</span>
            {s.expected && <span className="text-status-success ml-1">→ {s.expected}</span>}
          </li>
        ))}
      </ol>
    )
  } catch {
    return <span className="text-xs max-w-[230px] inline-block break-words">{steps}</span>
  }
}
