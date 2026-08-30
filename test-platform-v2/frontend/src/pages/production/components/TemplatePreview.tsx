import { Badge, Card, CardContent, CardHeader, CardTitle, Skeleton } from '@/ui'
import type { BuildTemplateResult, MaterializeTemplateResult } from '@/api/production'
import { TEMPLATE_VALIDATION_LABELS } from '@/api/production'
import { FileCheck, ShieldCheck } from '@/lib/icons'

interface TemplatePreviewProps {
  template: BuildTemplateResult | null
  materialization?: MaterializeTemplateResult | null
  loading?: boolean
}

/** Show a built template plus its validation_status and optional materialization result. */
export function TemplatePreview({ template, materialization = null, loading = false }: TemplatePreviewProps) {
  if (loading) return <Skeleton className="h-24 w-full" />
  if (!template) return <p className="py-4 text-sm text-muted-foreground">暂无模板。先「构建模板」。</p>

  const statusMeta = TEMPLATE_VALIDATION_LABELS[template.validation_status]
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex flex-wrap items-center gap-2">
          <FileCheck className="size-4" />
          模板 #{template.id}
          <Badge tone="neutral" className={statusMeta?.color}>{statusMeta?.label ?? template.validation_status}</Badge>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-2 text-sm">
        <div className="flex items-center gap-2 text-muted-foreground">
          <ShieldCheck className="size-3.5" />
          <span>校验状态：<span className="font-medium text-foreground">{template.validation_status}</span></span>
        </div>
        {materialization && (
          <div className="rounded-md border bg-status-success-muted px-3 py-2 text-status-success">
            物化成功 · materialization_id <span className="font-mono">#{materialization.materialization_id}</span>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
