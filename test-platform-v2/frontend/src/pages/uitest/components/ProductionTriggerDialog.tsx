import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { getEnvironment } from '../uiShared'
import type { Environment, UiJobItem } from '@/types'

interface ProductionTriggerDialogProps {
  target: UiJobItem | null
  triggering: boolean
  environments: Environment[]
  onOpenChange: (open: boolean) => void
  onConfirm: () => void
}

export default function ProductionTriggerDialog({
  target,
  triggering,
  environments,
  onOpenChange,
  onConfirm,
}: ProductionTriggerDialogProps) {
  return (
    <AlertDialog open={!!target} onOpenChange={onOpenChange}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle className="text-destructive">确认执行生产环境 UI 自动化？</AlertDialogTitle>
          <AlertDialogDescription asChild>
            <div className="space-y-2 text-sm">
              <p>该操作将启动真实浏览器并访问生产目标。请确认脚本仅包含已获授权的只读范围。</p>
              <dl className="rounded-md border p-3 text-foreground">
                <div><dt className="inline text-muted-foreground">任务：</dt><dd className="inline">{target?.name}</dd></div>
                <div><dt className="inline text-muted-foreground">环境：</dt><dd className="inline">{target ? getEnvironment(environments, target)?.name : '-'}</dd></div>
                <div className="break-all"><dt className="inline text-muted-foreground">地址：</dt><dd className="inline">{target ? getEnvironment(environments, target)?.base_url || '未配置' : '-'}</dd></div>
                <div className="break-all"><dt className="inline text-muted-foreground">脚本：</dt><dd className="inline">{target?.test_spec || '未配置'}</dd></div>
              </dl>
            </div>
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel disabled={triggering}>取消</AlertDialogCancel>
          <AlertDialogAction variant="destructive" disabled={triggering} onClick={onConfirm}>
            {triggering ? '正在触发…' : '确认执行生产任务'}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}
