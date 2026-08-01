import { useEffect, useState } from 'react'

import { AlertTriangle, ShieldCheck } from '@/lib/icons'
import { Badge } from '@/ui'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogMedia,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { Checkbox } from '@/components/ui/checkbox'
import { Label } from '@/components/ui/label'

export interface ProductionOperationDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  project: string
  environment: string
  baseUrl: string
  operation: string
  classification: 'read' | 'write'
  affectedCount: number
  isProduction: boolean
  pending?: boolean
  onConfirm: () => void | Promise<void>
}

export default function ProductionOperationDialog({
  open,
  onOpenChange,
  project,
  environment,
  baseUrl,
  operation,
  classification,
  affectedCount,
  isProduction,
  pending = false,
  onConfirm,
}: ProductionOperationDialogProps) {
  const [productionAcknowledged, setProductionAcknowledged] = useState(false)

  useEffect(() => {
    setProductionAcknowledged(false)
  }, [open, project, environment, baseUrl, operation])

  const confirmDisabled = pending || (isProduction && !productionAcknowledged)
  const environmentKind = isProduction ? '生产环境' : '测试环境'

  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent
        className="sm:max-w-lg"
        onKeyDown={(event) => {
          if (event.key !== 'Enter') return
          event.preventDefault()
          event.stopPropagation()
        }}
      >
        <AlertDialogHeader>
          <AlertDialogMedia className={isProduction ? 'bg-status-danger-muted text-status-danger' : 'bg-status-info-muted text-status-info'}>
            {isProduction
              ? <AlertTriangle className="size-5" aria-hidden="true" />
              : <ShieldCheck className="size-5" aria-hidden="true" />}
          </AlertDialogMedia>
          <AlertDialogTitle>确认{environmentKind}操作</AlertDialogTitle>
          <AlertDialogDescription>
            {isProduction
              ? '将向真实生产服务发送请求。请逐项核对目标与影响范围，确认后操作仍会接受服务端安全校验。'
              : '这是测试环境操作。请核对目标与影响范围，避免将测试请求误发到其他环境。'}
          </AlertDialogDescription>
        </AlertDialogHeader>

        <dl className="grid grid-cols-[5.5rem_minmax(0,1fr)] gap-x-3 gap-y-2 rounded-lg border bg-muted/20 p-3 text-sm">
          <dt className="text-muted-foreground">项目</dt>
          <dd className="min-w-0 font-medium break-words">{project}</dd>
          <dt className="text-muted-foreground">环境</dt>
          <dd className="min-w-0 font-medium break-words">{environment}</dd>
          <dt className="text-muted-foreground">Base URL</dt>
          <dd className="min-w-0 font-mono text-xs break-all">{baseUrl}</dd>
          <dt className="text-muted-foreground">操作</dt>
          <dd className="min-w-0 break-words">{operation}</dd>
          <dt className="text-muted-foreground">分类</dt>
          <dd>
            <Badge
              tone="neutral"
              className={classification === 'write'
                ? 'border-status-warning-border bg-status-warning-muted text-status-warning'
                : 'border-status-info-border bg-status-info-muted text-status-info'}
            >
              {classification === 'write' ? '写操作' : '读操作'}
            </Badge>
          </dd>
          <dt className="text-muted-foreground">影响数量</dt>
          <dd className="font-medium">{affectedCount} 个资源</dd>
        </dl>

        {isProduction && (
          <div className="flex items-start gap-3 rounded-lg border border-status-danger-border bg-status-danger-muted p-3">
            <Checkbox
              id="production-operation-acknowledgement"
              checked={productionAcknowledged}
              disabled={pending}
              onCheckedChange={(checked) => setProductionAcknowledged(checked === true)}
            />
            <Label
              htmlFor="production-operation-acknowledgement"
              className="cursor-pointer text-sm leading-5 text-foreground"
            >
              我已核对以上生产目标、Base URL 与影响数量，并确认执行此操作。
            </Label>
          </div>
        )}

        <AlertDialogFooter>
          <AlertDialogCancel disabled={pending}>取消</AlertDialogCancel>
          <AlertDialogAction
            variant={isProduction ? 'destructive' : 'default'}
            disabled={confirmDisabled}
            onClick={onConfirm}
          >
            {pending ? '执行中…' : `确认执行${isProduction ? '生产' : '测试'}操作`}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}
