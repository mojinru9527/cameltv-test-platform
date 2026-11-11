import { Badge, Card, CardContent } from '@/ui'
import type { DefectItem } from '@/types'

interface AiqaLinkSectionProps {
  defect: DefectItem
}

export default function AiqaLinkSection({ defect }: AiqaLinkSectionProps) {
  if (!defect.aiqe_run_id) return null

  const steps = defect.reproduction_steps ?? []
  const evidenceRefs = defect.evidence_refs ?? []
  const acRefs = defect.ac_refs ?? []

  return (
    <Card size="sm" className="mt-4">
      <div className="text-sm font-medium px-[var(--card-spacing)] pt-[var(--card-spacing)]">
        AIQE 关联执行
      </div>
      <CardContent className="space-y-3">
        <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-sm">
          <dt className="text-muted-foreground">linked execution</dt>
          <dd className="font-mono text-xs break-all">{defect.aiqe_run_id}</dd>
          {defect.aiqe_node_run_id && (
            <>
              <dt className="text-muted-foreground">node run</dt>
              <dd className="font-mono text-xs break-all">{defect.aiqe_node_run_id}</dd>
            </>
          )}
        </dl>

        {acRefs.length > 0 && (
          <div className="space-y-1.5">
            <div className="text-sm text-muted-foreground">验收标准（AC）</div>
            <div className="flex flex-wrap gap-1.5">
              {acRefs.map((ac) => (
                <Badge key={ac} tone="neutral">
                  {ac}
                </Badge>
              ))}
            </div>
          </div>
        )}

        {steps.length > 0 && (
          <div className="space-y-1.5">
            <div className="text-sm text-muted-foreground">结构化复现步骤</div>
            <ol className="list-decimal pl-5 space-y-1 text-sm">
              {steps.map((step, index) => (
                <li key={index}>
                  {step.action} → 预期：{step.expected}
                  {step.evidence_ref && (
                    <code className="ml-2 text-xs text-muted-foreground">{step.evidence_ref}</code>
                  )}
                </li>
              ))}
            </ol>
          </div>
        )}

        {evidenceRefs.length > 0 && (
          <div className="space-y-1.5">
            <div className="text-sm text-muted-foreground">证据</div>
            <div className="flex flex-wrap gap-1.5">
              {evidenceRefs.map((ref) => (
                <code key={ref} className="text-xs bg-muted rounded px-1.5 py-0.5">
                  {ref}
                </code>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
