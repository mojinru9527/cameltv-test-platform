import { Badge, type BadgeTone } from '@/ui'

/** Severity badge for a data-plan risk level (P0..P3). */
const RISK_MAP: Record<string, { label: string; tone: BadgeTone }> = {
  P0: { label: 'P0-致命', tone: 'danger' },
  P1: { label: 'P1-严重', tone: 'warning' },
  P2: { label: 'P2-一般', tone: 'info' },
  P3: { label: 'P3-建议', tone: 'neutral' },
}

export interface DataPlanRiskBadgeProps {
  riskLevel: string
  className?: string
}

export function DataPlanRiskBadge({ riskLevel, className }: DataPlanRiskBadgeProps) {
  const meta = RISK_MAP[riskLevel]
  if (!meta) {
    return (
      <Badge variant="outline" className={className}>
        {riskLevel || 'N/A'}
      </Badge>
    )
  }
  return (
    <Badge tone={meta.tone} className={className}>
      {meta.label}
    </Badge>
  )
}
