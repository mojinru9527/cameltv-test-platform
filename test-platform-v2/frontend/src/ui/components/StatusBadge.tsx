import { type ReactNode } from 'react'
import { Badge, type BadgeTone } from '../primitives/Badge'

export type StatusVariant = 'pass' | 'fail' | 'running' | 'pending' | 'blocked' | 'skipped'
export type SeverityVariant = 'P0' | 'P1' | 'P2' | 'P3'

const statusMap: Record<StatusVariant, { label: string; tone: BadgeTone }> = {
  pass: { label: '通过', tone: 'success' },
  fail: { label: '失败', tone: 'danger' },
  running: { label: '运行中', tone: 'info' },
  pending: { label: '待执行', tone: 'neutral' },
  blocked: { label: '阻断', tone: 'warning' },
  skipped: { label: '跳过', tone: 'neutral' },
}

const severityMap: Record<SeverityVariant, { label: string; tone: BadgeTone }> = {
  P0: { label: 'P0-致命', tone: 'danger' },
  P1: { label: 'P1-严重', tone: 'warning' },
  P2: { label: 'P2-一般', tone: 'info' },
  P3: { label: 'P3-建议', tone: 'neutral' },
}

function isSeverity(v: string): v is SeverityVariant {
  return v === 'P0' || v === 'P1' || v === 'P2' || v === 'P3'
}

export interface StatusBadgeProps {
  variant: StatusVariant | SeverityVariant
  label?: string
  className?: string
  children?: ReactNode
}

export function StatusBadge({ variant, label, className, children }: StatusBadgeProps) {
  const config = isSeverity(variant) ? severityMap[variant] : statusMap[variant]
  return (
    <Badge tone={config.tone} className={className}>
      {children ?? label ?? config.label}
    </Badge>
  )
}
