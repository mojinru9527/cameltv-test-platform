import { Badge, Button, Card, CardContent, CardHeader, CardTitle } from '@/ui'
import { APPROVAL_STATUS_LABELS, type ApprovalRequest } from '@/api/runtime'

interface Props {
  approval: ApprovalRequest
  onApprove?: (id: number) => void
  onReject?: (id: number) => void
}

/** A gate card shown to testers when a Run needs approval before a dangerous step (V34-017). */
export function ApprovalGateCard({ approval, onApprove, onReject }: Props) {
  const status = APPROVAL_STATUS_LABELS[approval.status]
  const pending = approval.status === 'PENDING'
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          审批 #{approval.id}
          <Badge tone="neutral" className={status?.color}>{status?.label ?? approval.status}</Badge>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="text-sm">
          <div className="text-muted-foreground">操作</div>
          <div className="font-medium">{approval.action_type}</div>
        </div>
        <div className="text-sm">
          <div className="text-muted-foreground">决策</div>
          <div className="font-medium">{approval.policy_decision}</div>
        </div>
        {pending && (
          <div className="flex gap-2 pt-1">
            {onApprove && <Button size="sm" onClick={() => onApprove(approval.id)}>批准</Button>}
            {onReject && <Button size="sm" variant="secondary" onClick={() => onReject(approval.id)}>拒绝</Button>}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
