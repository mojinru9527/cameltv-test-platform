import { Badge } from '@/ui'
import { type CommandIR } from '@/api/actionPlans'
import { CommandDiff } from './CommandDiff'
import { OracleChangeGuardBadge } from './OracleChangeGuardBadge'

export interface HealingProposalDiffProps {
  before: CommandIR | null
  after: CommandIR | null
  /** Whether the oracle key set changed between the two revisions. */
  oracleChanged?: boolean
  /** Optional label for the healing proposal being reviewed. */
  proposalLabel?: string
}

/**
 * Before / after diff for a healing proposal. Surfaces the Command IR change
 * and always shows the Oracle-change guard so a reviewer keeps the risk in view.
 */
export function HealingProposalDiff({
  before,
  after,
  oracleChanged = false,
  proposalLabel,
}: HealingProposalDiffProps) {
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap items-center gap-2">
          <h3 className="text-sm font-semibold">愈合前后对比</h3>
          {proposalLabel && <Badge variant="outline">{proposalLabel}</Badge>}
        </div>
        <OracleChangeGuardBadge changed={oracleChanged} />
      </div>
      <CommandDiff before={before} after={after} />
    </div>
  )
}
