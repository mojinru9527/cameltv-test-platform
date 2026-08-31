import { Badge } from '@/ui'
import type { Campaign } from '@/api/continuous'
import { cn } from '@/lib/utils'
import {
  type CampaignProgressCounts,
  deriveCampaignGate,
  deriveCampaignProgress,
} from './campaignProgressCounts'

export interface CampaignProgressProps {
  campaign?: Campaign | null
  className?: string
}

interface StageDef {
  key: 'selected' | 'queued' | 'running' | 'finished'
  label: string
}

const STAGES: StageDef[] = [
  { key: 'selected', label: 'Selected' },
  { key: 'queued', label: 'Queued' },
  { key: 'running', label: 'Running' },
  { key: 'finished', label: 'Finished' },
]

/** Which stage is currently "active" for highlighting, derived from the counts. */
function activeStageKey(counts: CampaignProgressCounts): StageDef['key'] {
  if (counts.selected > 0 && counts.finished === counts.selected) return 'finished'
  if (counts.running > 0) return 'running'
  if (counts.queued > 0) return 'queued'
  return 'selected'
}

/**
 * Current execution progress of a campaign (Selected → Queued → Running → Finished)
 * plus the quality-gate state (WAITING / Evaluated).
 */
export function CampaignProgress({ campaign, className }: CampaignProgressProps) {
  const counts = deriveCampaignProgress(campaign)
  const gate = deriveCampaignGate(campaign)
  const active = activeStageKey(counts)

  return (
    <div className={cn('flex flex-wrap items-center gap-2 text-xs', className)}>
      {STAGES.map((stage, idx) => {
        const value = counts[stage.key]
        const isActive = stage.key === active
        return (
          <span key={stage.key} className="flex items-center gap-1.5">
            {idx > 0 && <span className="text-muted-foreground/40">→</span>}
            <Badge
              variant="outline"
              className={isActive ? 'bg-status-info-muted text-status-info' : 'bg-muted text-muted-foreground'}
            >
              {stage.label}: {value}
            </Badge>
          </span>
        )
      })}
      <Badge tone={gate === 'EVALUATED' ? 'success' : 'warning'}>Gate: {gate}</Badge>
    </div>
  )
}
