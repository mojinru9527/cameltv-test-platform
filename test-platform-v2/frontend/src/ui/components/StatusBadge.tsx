import { Badge, type BadgeTone } from '../primitives/Badge'

export type StatusVariant = 'pass' | 'fail' | 'running' | 'pending' | 'blocked' | 'skipped'

const statusMap: Record<StatusVariant, { label: string; tone: BadgeTone }> = {
  pass: { label: '通过', tone: 'success' },
  fail: { label: '失败', tone: 'danger' },
  running: { label: '运行中', tone: 'info' },
  pending: { label: '待执行', tone: 'neutral' },
  blocked: { label: '阻断', tone: 'warning' },
  skipped: { label: '跳过', tone: 'neutral' },
}

export interface StatusBadgeProps {
  variant: StatusVariant
  label?: string
  className?: string
}

export function StatusBadge({ variant, label, className }: StatusBadgeProps) {
  const config = statusMap[variant]
  return (
    <Badge tone={config.tone} className={className}>
      {label ?? config.label}
    </Badge>
  )
}
