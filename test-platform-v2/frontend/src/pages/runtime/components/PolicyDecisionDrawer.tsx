import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog'

interface PolicyDecision {
  decision: 'ALLOW' | 'DENY' | 'REQUIRE_APPROVAL'
  reason: string
}

const DECISION_COLOR: Record<string, string> = {
  ALLOW: 'bg-status-success-muted text-status-success',
  DENY: 'bg-status-danger-muted text-status-danger',
  REQUIRE_APPROVAL: 'bg-status-warning-muted text-status-warning',
}

interface Props {
  open: boolean
  onClose: () => void
  decision: PolicyDecision | null
}

/** Drawer that shows a Policy Gateway decision (reason + diff) for a driver action. */
export function PolicyDecisionDrawer({ open, onClose, decision }: Props) {
  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>政策判定</DialogTitle>
          <DialogDescription>安全策略网关对该驱动动作的判定</DialogDescription>
        </DialogHeader>
        {decision ? (
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <span className={`rounded px-2 py-0.5 text-sm ${DECISION_COLOR[decision.decision] ?? 'bg-muted text-muted-foreground'}`}>
                {decision.decision}
              </span>
            </div>
            <p className="text-sm text-muted-foreground">{decision.reason}</p>
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">暂无判定</p>
        )}
      </DialogContent>
    </Dialog>
  )
}
