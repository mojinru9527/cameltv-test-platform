import { Badge } from '@/ui'
import { Button } from '@/ui'
import { Card, CardContent } from '@/components/ui/card'
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  AlertTriangle,
  Ban,
  FileText,
  Image,
  Loader2,
  Monitor,
  RotateCcw,
  Terminal,
  Video,
  XCircle,
} from '@/lib/icons'
import { execStatusLabel } from '@/utils/executionStatus'
import { BROWSER_MAP, browserBadgeClass, statusBadgeClass } from '../uiShared'
import { ProtectedArtifactMedia } from './ProtectedArtifactMedia'
import type { UiRunArtifact, UiRunItem } from '@/types'

interface UiRunDetailDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  run: UiRunItem | null
  loading: boolean
  artifacts: UiRunArtifact[]
  onCancelRun: () => void
  onRefresh: () => void
}

export default function UiRunDetailDialog({
  open,
  onOpenChange,
  run,
  loading,
  artifacts,
  onCancelRun,
  onRefresh,
}: UiRunDetailDialogProps) {
  return (
    <Dialog open={open} onOpenChange={(open) => { if (!open) onOpenChange(false) }}>
      <DialogContent className="sm:max-w-2xl max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            运行详情 #{run?.id}
            {run && (
              <Badge tone="neutral" className={statusBadgeClass(run.status)}>
                {execStatusLabel(run.status)}
              </Badge>
            )}
          </DialogTitle>
        </DialogHeader>

        {loading && !run ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="size-6 animate-spin" />
          </div>
        ) : run ? (
          <div className="flex flex-col gap-4">
            {/* Info grid */}
            <dl className="grid grid-cols-2 border rounded-lg">
              {[
                ['状态', <Badge key="st" tone="neutral" className={statusBadgeClass(run.status)}>{execStatusLabel(run.status)}</Badge>],
                ['浏览器', run.browser ? <Badge key="br" tone="neutral" className={browserBadgeClass(BROWSER_MAP[run.browser]?.color)}><Monitor className="size-3" />{run.browser}</Badge> : '-'],
                ['Base URL', run.base_url || '-'],
                ['耗时', run.duration != null ? `${run.duration}s` : '-'],
                ['开始时间', run.started_at ? new Date(run.started_at).toLocaleString() : '-'],
                ['结束时间', run.finished_at ? new Date(run.finished_at).toLocaleString() : '-'],
                ['进程 ID', run.process_id != null ? String(run.process_id) : '-'],
              ].map(([label, value], i) => (
                <div key={i} className={`flex flex-col border-b border-r p-2 even:border-r-0 ${i >= 6 ? 'border-b-0' : ''}`}>
                  <dt className="text-xs text-muted-foreground">{label}</dt>
                  <dd className="text-sm mt-0.5 break-all">{value}</dd>
                </div>
              ))}
            </dl>

            {/* Error message */}
            {run.error_message && (
              <div className="rounded-lg border border-status-danger-border bg-status-danger-muted p-3 dark:border-status-danger-border dark:bg-status-danger-muted">
                <div className="flex items-center gap-2 text-sm font-medium text-status-danger dark:text-status-danger">
                  <AlertTriangle className="size-4" />
                  错误信息
                </div>
                <pre className="mt-1 whitespace-pre-wrap text-xs text-status-danger dark:text-status-danger">{run.error_message}</pre>
              </div>
            )}

            {/* Actions */}
            <div className="flex items-center gap-2 flex-wrap">
              {(run.status === 'pending' || run.status === 'running') && (
                <Button variant="secondary" size="sm" onClick={onCancelRun} className="text-destructive border-destructive/20 hover:bg-destructive/10">
                  <Ban className="size-4" />
                  取消运行
                </Button>
              )}
              {run.status !== 'pending' && run.status !== 'running' && (
                <Button variant="secondary" size="sm" onClick={onRefresh}>
                  <RotateCcw className="size-4" />
                  刷新
                </Button>
              )}
            </div>

            {/* Result summary */}
            {run.result && (run.result.total != null) && (
              <div className="flex gap-3 flex-wrap">
                <div className="rounded-lg border px-3 py-2 text-center min-w-[70px]">
                  <div className="text-xs text-muted-foreground">总计</div>
                  <div className="text-lg font-semibold">{run.result.total}</div>
                </div>
                <div className="rounded-lg border border-status-success-border bg-status-success-muted px-3 py-2 text-center min-w-[70px] dark:border-status-success-border dark:bg-status-success-muted">
                  <div className="text-xs text-status-success dark:text-status-success">通过</div>
                  <div className="text-lg font-semibold text-status-success dark:text-status-success">{run.result.pass_ ?? '-'}</div>
                </div>
                <div className="rounded-lg border border-status-danger-border bg-status-danger-muted px-3 py-2 text-center min-w-[70px] dark:border-status-danger-border dark:bg-status-danger-muted">
                  <div className="text-xs text-status-danger dark:text-status-danger">失败</div>
                  <div className="text-lg font-semibold text-status-danger dark:text-status-danger">{run.result.fail ?? '-'}</div>
                </div>
                <div className="rounded-lg border px-3 py-2 text-center min-w-[70px]">
                  <div className="text-xs text-muted-foreground">跳过</div>
                  <div className="text-lg font-semibold">{run.result.skip ?? '-'}</div>
                </div>
              </div>
            )}

            {/* Stdout/Stderr toggle */}
            <Tabs defaultValue={run.stdout ? 'stdout' : run.stderr ? 'stderr' : 'none'}>
              <TabsList>
                <TabsTrigger value="" disabled>输出</TabsTrigger>
                {(run.stdout) && <TabsTrigger value="stdout"><Terminal className="size-3" />stdout</TabsTrigger>}
                {(run.stderr) && <TabsTrigger value="stderr"><XCircle className="size-3" />stderr</TabsTrigger>}
              </TabsList>
              {run.stdout && (
                <TabsContent value="stdout" className="mt-3">
                  <Card size="sm">
                    <CardContent>
                      <pre className="whitespace-pre-wrap m-0 text-xs max-h-[300px] overflow-y-auto font-mono">{run.stdout}</pre>
                    </CardContent>
                  </Card>
                </TabsContent>
              )}
              {run.stderr && (
                <TabsContent value="stderr" className="mt-3">
                  <Card size="sm">
                    <CardContent>
                      <pre className="whitespace-pre-wrap m-0 text-xs max-h-[300px] overflow-y-auto font-mono text-status-danger dark:text-status-danger">{run.stderr}</pre>
                    </CardContent>
                  </Card>
                </TabsContent>
              )}
            </Tabs>

            {/* Artifacts */}
            {artifacts.length > 0 && (
              <div className="space-y-2">
                <h4 className="text-sm font-medium flex items-center gap-2">
                  <FileText className="size-4" />
                  产物 ({artifacts.length})
                </h4>
                {/* Screenshots */}
                {artifacts.filter(a => a.type === 'png').length > 0 && (
                  <div>
                    <div className="text-xs text-muted-foreground mb-2 flex items-center gap-1"><Image className="size-3" />截图</div>
                    <div className="grid grid-cols-3 gap-2">
                      {artifacts.filter(a => a.type === 'png').slice(0, 9).map((a) => (
                        <ProtectedArtifactMedia key={a.path} runId={run.id} path={a.path} name={a.name} kind="image" />
                      ))}
                    </div>
                  </div>
                )}
                {/* Videos */}
                {artifacts.filter(a => a.type === 'webm').map((a) => (
                  <div key={a.path} className="rounded border overflow-hidden">
                    <div className="text-xs text-muted-foreground p-2 flex items-center gap-1"><Video className="size-3" />视频: {a.name}</div>
                    <ProtectedArtifactMedia runId={run.id} path={a.path} name={a.name} kind="video" />
                  </div>
                ))}
                {/* Traces */}
                {artifacts.filter(a => a.type === 'zip').map((a) => (
                  <div key={a.path}>
                    <ProtectedArtifactMedia runId={run.id} path={a.path} name={`下载 Trace: ${a.name}`} kind="download" />
                  </div>
                ))}
                {/* Other files */}
                {artifacts.filter(a => !['png', 'webm', 'zip'].includes(a.type)).length > 0 && (
                  <div className="text-xs text-muted-foreground flex flex-wrap gap-2">
                    其他文件:
                    {artifacts.filter(a => !['png', 'webm', 'zip'].includes(a.type)).map((a) => (
                      <ProtectedArtifactMedia key={a.path} runId={run.id} path={a.path} name={a.name} kind="download" />
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* HTML Report link */}
            {run.html_report_path && (
              <ProtectedArtifactMedia runId={run.id} path="report/index.html" name="查看 HTML 报告" kind="link" />
            )}

            {/* Empty artifacts for pending/running */}
            {artifacts.length === 0 && (run.status === 'pending' || run.status === 'running') && (
              <div className="flex items-center gap-2 text-sm text-muted-foreground py-4 justify-center">
                <Loader2 className="size-4 animate-spin" />
                运行中，产物将在完成后显示...
              </div>
            )}
            {artifacts.length === 0 && run.status !== 'pending' && run.status !== 'running' && (
              <p className="text-sm text-muted-foreground text-center py-4">暂无产物文件</p>
            )}
          </div>
        ) : (
          <p className="text-sm text-muted-foreground text-center py-12">加载失败</p>
        )}

        <DialogFooter>
          <Button variant="secondary" onClick={() => onOpenChange(false)}>关闭</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
