import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/ui'
import { Card, CardContent } from '@/components/ui/card'
import { CheckCircle2, Info } from '@/lib/icons'
import type { RequirementAnalysis } from '@/types'
import { SEVERITY_BADGE_CLASSES, SEVERITY_CONFIG } from './AiDisplayParts'

export default function AiAnalysisPanel({ analysis }: { analysis: RequirementAnalysis }) {
  const { extracted_requirements, overall_assessment } = analysis
  const typeLabels: Record<string, string> = { functional: '功能', ui: '界面', data: '数据', integration: '集成' }

  return (
    <div className="max-h-[60vh] overflow-auto px-1">
      {overall_assessment && (
        <Alert className="mb-4">
          <Info className="size-4" />
          <AlertTitle>整体评估</AlertTitle>
          <AlertDescription>{overall_assessment}</AlertDescription>
        </Alert>
      )}

      {extracted_requirements.map((er) => {
        const issueCount = er.issues?.length || 0
        const hasHighIssue = er.issues?.some((i) => i.severity === 'high')
        const hasMediumIssue = er.issues?.some((i) => i.severity === 'medium')
        const issueBadgeClass = hasHighIssue
          ? 'border-status-danger-border bg-status-danger-muted text-status-danger'
          : hasMediumIssue
            ? 'border-status-warning-border bg-status-warning-muted text-status-warning'
            : 'border-status-info-border bg-status-info-muted text-status-info'

        return (
          <Card key={er.id} size="sm" className="mb-3">
            <CardContent className="pt-3">
              <div className="flex items-center gap-2 flex-wrap mb-2">
                <Badge tone="neutral" className="border-status-accent-border bg-status-accent-muted text-status-accent">
                  {er.id}
                </Badge>
                <span className="font-medium text-sm">{er.title}</span>
                <Badge tone="neutral">{typeLabels[er.type] || er.type}</Badge>
                {issueCount > 0 && (
                  <Badge tone="neutral" className={issueBadgeClass}>
                    {issueCount} 问题
                  </Badge>
                )}
              </div>
              <p className="text-sm text-muted-foreground mb-3">{er.description}</p>

              {(er.issues || []).map((iss, idx) => (
                <div
                  key={idx}
                  style={{ borderColor: SEVERITY_CONFIG[iss.severity]?.color || 'var(--border)' }}
                  className="mb-2 rounded border bg-muted/50 p-2"
                >
                  <div className="flex items-center gap-2">
                    <Badge
                      tone="neutral"
                      className={SEVERITY_BADGE_CLASSES[iss.severity] || 'border-border bg-muted text-muted-foreground'}
                    >
                      {SEVERITY_CONFIG[iss.severity]?.label || iss.severity}
                    </Badge>
                    <span className="text-sm">{iss.description}</span>
                  </div>
                  {iss.suggestion && (
                    <p className="mt-1 text-xs text-muted-foreground">
                      建议：{iss.suggestion}
                    </p>
                  )}
                </div>
              ))}

              {issueCount === 0 && (
                <span className="inline-flex items-center gap-1 text-xs text-status-success"><CheckCircle2 className="size-3.5" aria-hidden="true" />无明显问题</span>
              )}
            </CardContent>
          </Card>
        )
      })}

      {extracted_requirements.length === 0 && (
        <div className="text-center py-5 text-muted-foreground">未提取到需求功能点</div>
      )}
    </div>
  )
}
