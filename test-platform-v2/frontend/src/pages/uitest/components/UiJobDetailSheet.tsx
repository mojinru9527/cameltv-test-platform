import { Badge } from '@/ui'
import { Button } from '@/ui'
import { Card, CardContent } from '@/components/ui/card'
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Monitor, Play } from '@/lib/icons'
import { execStatusLabel } from '@/utils/executionStatus'
import { BROWSER_MAP, browserBadgeClass, getEnvironment, isProductionJob, statusBadgeClass } from '../uiShared'
import UiRunResultSummary from './UiRunResultSummary'
import type { Environment, UiJobItem, UiRunItem } from '@/types'

interface UiJobDetailSheetProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  detail: any
  runs: { total: number; items: UiRunItem[] }
  environments: Environment[]
  hasPerm: (perm: string) => boolean
  onRequestTrigger: (job: UiJobItem) => void
  onOpenRunDetail: (run: UiRunItem) => void
}

export default function UiJobDetailSheet({
  open,
  onOpenChange,
  detail,
  runs,
  environments,
  hasPerm,
  onRequestTrigger,
  onOpenRunDetail,
}: UiJobDetailSheetProps) {
  return (
    <Sheet open={open} onOpenChange={(open) => { if (!open) onOpenChange(false) }}>
      <SheetContent className="sm:max-w-3xl">
        <SheetHeader>
          <SheetTitle>任务详情</SheetTitle>
        </SheetHeader>
        {detail && (
          <div className="flex flex-col gap-4 mt-4 overflow-y-auto flex-1">
            <dl className="grid grid-cols-2 border rounded-lg">
              {[
                ['名称', detail.name],
                ['浏览器', <Badge key="br" tone="neutral" className={browserBadgeClass(BROWSER_MAP[detail.browser]?.color)}><Monitor className="size-3" />{detail.browser}</Badge>],
                ['状态', <Badge key="st" tone="neutral" className={statusBadgeClass(detail.status)}>{execStatusLabel(detail.status)}</Badge>],
                ['测试文件', detail.test_spec || '-'],
                ['目标环境', getEnvironment(environments, detail)?.name || '未绑定'],
                ['目标地址', getEnvironment(environments, detail)?.base_url || '-'],
              ].map(([label, value]) => (
                <div key={label as string} className="flex flex-col border-b border-r p-2 even:border-r-0 [&:nth-last-child(-n+2)]:border-b-0">
                  <dt className="text-xs text-muted-foreground">{label}</dt>
                  <dd className="text-sm mt-0.5">{value}</dd>
                </div>
              ))}
              <div className="flex flex-col border-b border-r p-2 even:border-r-0 col-span-2 border-r-0 border-b-0">
                <dt className="text-xs text-muted-foreground">描述</dt>
                <dd className="text-sm mt-0.5">{detail.description || '-'}</dd>
              </div>
            </dl>

            {hasPerm('uitest:trigger') && (
              <div>
                <Button
                  onClick={() => onRequestTrigger(detail)}
                  disabled={isProductionJob(environments, detail) && !hasPerm('uitest:trigger_prod')}
                  title={isProductionJob(environments, detail) && !hasPerm('uitest:trigger_prod') ? '缺少 uitest:trigger_prod 生产执行权限' : undefined}
                >
                  <Play className="size-4" />
                  执行测试
                </Button>
              </div>
            )}

            <Tabs defaultValue="runs">
              <TabsList>
                <TabsTrigger value="runs">运行历史 ({runs.total})</TabsTrigger>
                <TabsTrigger value="result">最新结果</TabsTrigger>
              </TabsList>
              <TabsContent value="runs" className="mt-3">
                <div className="rounded-lg border">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead className="w-[80px]">状态</TableHead>
                        <TableHead className="w-[170px]">开始时间</TableHead>
                        <TableHead className="w-[170px]">结束时间</TableHead>
                        <TableHead className="w-[200px]">结果</TableHead>
                        <TableHead className="w-[120px]">Trace</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {runs.items.length === 0 ? (
                        <TableRow>
                          <TableCell colSpan={5} className="text-center py-4 text-muted-foreground">暂无数据</TableCell>
                        </TableRow>
                      ) : (
                        runs.items.map((run) => (
                          <TableRow key={run.id} className="cursor-pointer hover:bg-muted/50" onClick={() => onOpenRunDetail(run)}>
                            <TableCell>
                              <Badge tone="neutral" className={statusBadgeClass(run.status)}>
                                {execStatusLabel(run.status)}
                              </Badge>
                            </TableCell>
                            <TableCell>{run.started_at ? new Date(run.started_at).toLocaleString() : '-'}</TableCell>
                            <TableCell>{run.finished_at ? new Date(run.finished_at).toLocaleString() : '-'}</TableCell>
                            <TableCell>
                              {run.result ? `总计 ${run.result.total} · 通过 ${run.result.pass_} · 失败 ${run.result.fail}` : '-'}
                            </TableCell>
                            <TableCell className="max-w-[120px] truncate">{run.trace_id || '-'}</TableCell>
                          </TableRow>
                        ))
                      )}
                    </TableBody>
                  </Table>
                </div>
              </TabsContent>
              <TabsContent value="result" className="mt-3">
                {detail.last_result ? (
                  <Card size="sm">
                    <CardContent>
                      <UiRunResultSummary value={detail.last_result} />
                    </CardContent>
                  </Card>
                ) : (
                  <p className="text-sm text-muted-foreground text-center py-8">暂无结果</p>
                )}
              </TabsContent>
            </Tabs>
          </div>
        )}
      </SheetContent>
    </Sheet>
  )
}
