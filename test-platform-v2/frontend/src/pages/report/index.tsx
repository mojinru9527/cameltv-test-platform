import { useState } from 'react'
import { useChartColors } from '@/hooks/use-chart-colors'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { toast } from 'sonner'
import { createReport, deleteReport, exportReportUrl, fetchReport, fetchReports, fetchTrends, type TrendsData } from '@/api/report'
import { fetchPlans } from '@/api/testplan'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { cn } from '@/lib/utils'
import DataTable, { type DataTableColumn } from '@/components/DataTable'
import PageHeader from '@/components/PageHeader'
import { SkeletonText } from '@/components/ui/skeleton'
import { useApi } from '@/hooks/useApi'
import { ErrorState, AsyncState } from '@/components/state'
import StatCard from '@/components/StatCard'
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts'
import {
  Plus,
  Search,
  Eye,
  Trash2,
  CheckCircle2,
  XCircle,
  MinusCircle,
  StopCircle,
  Clock,
  Loader2,
  Download,
  FileDown,
  FileSpreadsheet,
  FileText,
  BarChart3,
  Bug,
  Percent,
  ArrowUp,
  ArrowDown,
} from '@/lib/icons'

// ── Status config ──
const STATUS_CONFIG: Record<string, { label: string; icon: typeof CheckCircle2; color: string; variant: 'default' | 'secondary' | 'destructive' | 'outline' }> = {
  pass: { label: 'pass', icon: CheckCircle2, color: 'text-green-500', variant: 'default' },
  fail: { label: 'fail', icon: XCircle, color: 'text-red-500', variant: 'destructive' },
  skip: { label: 'skip', icon: MinusCircle, color: 'text-yellow-500', variant: 'secondary' },
  block: { label: 'block', icon: StopCircle, color: 'text-muted-foreground', variant: 'outline' },
  pending: { label: 'pending', icon: Clock, color: 'text-muted-foreground', variant: 'outline' },
}

const PRIORITY_CONFIG: Record<string, 'default' | 'destructive' | 'secondary' | 'outline'> = {
  P0: 'destructive',
  P1: 'secondary',
  P2: 'default',
  P3: 'outline',
}

// ── Zod schemas ──
const reportSchema = z.object({
  plan_id: z.coerce.number({ invalid_type_error: '请选择计划' }),
  name: z.string().min(1, '请输入报告名称'),
  description: z.string().optional(),
  template_id: z.coerce.number().optional(),
})

type ReportFormData = z.infer<typeof reportSchema>

export default function ReportPage() {
  const chartColors = useChartColors()
  const [keyword, setKeyword] = useState('')
  const [page, setPage] = useState(1)
  const [createOpen, setCreateOpen] = useState(false)
  const [detailId, setDetailId] = useState<number | null>(null)
  const [detail, setDetail] = useState<any>(null)
  const [creating, setCreating] = useState(false)
  const [plans, setPlans] = useState<any[]>([])

  const {
    register,
    handleSubmit,
    formState: { errors },
    reset,
    setValue,
    watch,
  } = useForm<ReportFormData>({
    resolver: zodResolver(reportSchema),
  })
  const watchPlanId = watch('plan_id')

  // ── Data fetching with useApi ──
  const { data, isLoading, isRefetching, isError, error, refetch } = useApi(
    () => {
      const params: any = { page, page_size: 20 }
      if (keyword) params.keyword = keyword
      return fetchReports(params) as unknown as Promise<{ total: number; items: any[]; page: number; page_size: number }>
    },
    [keyword, page]
  )

  const items = data?.items || []
  const totalPages = data ? Math.max(1, Math.ceil(data.total / data.page_size)) : 1

  // ── Trends data ──
  const trendsState = useApi<TrendsData>(
    () => fetchTrends(),
    [],
  )

  // ── DataTable column definitions ──
  const reportColumns: DataTableColumn<any>[] = [
    { key: 'report_id', header: '编号', headerClassName: 'w-[150px]', className: 'max-w-[150px] truncate', render: (r) => r.report_id },
    { key: 'name', header: '名称', className: 'truncate', render: (r) => r.name },
    { key: 'plan_name', header: '关联计划', headerClassName: 'w-[160px]', className: 'max-w-[160px] truncate', render: (r) => r.plan_name || <span className="text-muted-foreground">—</span> },
    { key: 'template_id', header: '模板', headerClassName: 'w-[60px]', render: (r) => r.template_id ? <Badge variant="secondary" className="text-[10px]">#{r.template_id}</Badge> : <span className="text-muted-foreground">—</span> },
    { key: 'created_at', header: '创建时间', headerClassName: 'w-[170px]', render: (r) => r.created_at ? new Date(r.created_at).toLocaleString() : '-' },
    { key: 'actions', header: '操作', headerClassName: 'w-[120px]', render: (r) => (
      <div className="flex items-center gap-2">
        <Button size="sm" variant="outline" onClick={() => openDetail(r.id)} data-icon="inline-start">
          <Eye />
          查看
        </Button>
        <AlertDialog>
          <AlertDialogTrigger asChild>
            <Button size="sm" variant="destructive" data-icon="inline-start">
              <Trash2 />
            </Button>
          </AlertDialogTrigger>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>确定删除？</AlertDialogTitle>
              <AlertDialogDescription>
                将删除报告「{r.name}」，此操作不可撤销。
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>取消</AlertDialogCancel>
              <AlertDialogAction variant="destructive" onClick={() => doDelete(r.id)}>
                删除
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </div>
    )},
  ]

  // ── Actions ──
  const loadPlans = async () => {
    try {
      const r: any = await fetchPlans({ page_size: 200 })
      setPlans(r.items || [])
    } catch { /* */ }
  }

  const openCreate = () => {
    loadPlans()
    reset({ plan_id: undefined as any, name: '', description: '' })
    setCreateOpen(true)
  }

  const doCreate = async (v: ReportFormData) => {
    setCreating(true)
    try {
      await createReport({ plan_id: v.plan_id, name: v.name, description: v.description, template_id: v.template_id })
      toast.success('报告已生成')
      setCreateOpen(false)
      refetch()
    } finally { setCreating(false) }
  }

  const doDelete = async (id: number) => {
    await deleteReport(id)
    toast.success('已删除')
    refetch()
  }

  const openDetail = async (id: number) => {
    setDetailId(id)
    try {
      const r: any = await fetchReport(id)
      setDetail(r)
    } catch { /* */ }
  }

  const handleSearch = () => {
    setPage(1)
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') setPage(1)
  }

  // detail content parsing
  const content = detail?.content
  const dStats = content?.stats || {}
  const dCases = content?.cases || []
  const dTotal = dStats.total || 0
  const dPassRate = dTotal > 0 ? Math.round(((dStats.pass_ || 0) / dTotal) * 100) : 0

  const statItems = [
    { key: 'pass', color: chartColors.barPass, value: dStats.pass_ || 0 },
    { key: 'fail', color: chartColors.barFail, value: dStats.fail || 0 },
    { key: 'skip', color: chartColors.chart4, value: dStats.skip || 0 },
    { key: 'block', color: chartColors.p3, value: dStats.block || 0 },
    { key: 'pending', color: chartColors.chart1, value: dStats.pending || 0 },
  ]

  return (
    <div>
      <PageHeader title="报告中心" />

      {/* ── Trend Section ── */}
      <AsyncState
        isLoading={trendsState.isLoading}
        isError={trendsState.isError}
        error={trendsState.error}
        data={trendsState.data}
        onRetry={trendsState.refetch}
        loadingVariant="skeleton"
        skeletonType="page"
        emptyTitle="暂无趋势数据"
        emptyDescription="生成多份报告后，系统将自动汇总趋势分析"
      >
        {(trends) => {
          const passRateData = trends.points.map((p) => ({
            ...p,
            dateLabel: p.date ? new Date(p.date).toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' }) : '',
          }))
          return (
            <div className="mb-6 space-y-4">
              {/* Summary cards */}
              <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                <StatCard icon={BarChart3} label="报告总数" value={trends.summary.total_reports} variant="glass" />
                <StatCard icon={Percent} label="平均通过率" value={`${trends.summary.avg_pass_rate}%`} variant="glass" />
                <StatCard icon={ArrowUp} label="最高通过率" value={`${trends.summary.best_pass_rate}%`} variant="glass" />
                <StatCard icon={ArrowDown} label="最低通过率" value={`${trends.summary.worst_pass_rate}%`} variant="glass" />
                <StatCard icon={Bug} label="待处理缺陷" value={trends.summary.latest_open_defects} variant="glass" />
              </div>

              {/* Charts */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                {/* Pass rate trend */}
                <Card>
                  <CardHeader><CardTitle>通过率趋势</CardTitle></CardHeader>
                  <CardContent>
                    <ResponsiveContainer width="100%" height={300}>
                      <LineChart data={passRateData}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="dateLabel" />
                        <YAxis domain={[0, 100]} tickFormatter={(v) => `${v}%`} />
                        <Tooltip
                          formatter={(value: any) => [`${value}%`, '通过率']}
                          labelFormatter={(label: any) => `日期: ${label}`}
                        />
                        <Legend />
                        <Line
                          type="monotone"
                          dataKey="pass_rate"
                          name="通过率"
                          stroke={chartColors.chart1}
                          strokeWidth={2}
                          dot={{ r: 4 }}
                          activeDot={{ r: 6 }}
                        />
                      </LineChart>
                    </ResponsiveContainer>
                  </CardContent>
                </Card>

                {/* Defect convergence trend */}
                <Card>
                  <CardHeader><CardTitle>缺陷收敛趋势</CardTitle></CardHeader>
                  <CardContent>
                    <ResponsiveContainer width="100%" height={300}>
                      <LineChart data={passRateData}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="dateLabel" />
                        <YAxis allowDecimals={false} />
                        <Tooltip />
                        <Legend />
                        <Line
                          type="monotone"
                          dataKey="open_p0"
                          name="P0 缺陷"
                          stroke={chartColors.barFail}
                          strokeWidth={2}
                          dot={{ r: 4 }}
                        />
                        <Line
                          type="monotone"
                          dataKey="open_p1"
                          name="P1 缺陷"
                          stroke={chartColors.chart4}
                          strokeWidth={2}
                          dot={{ r: 4 }}
                        />
                        <Line
                          type="monotone"
                          dataKey="open_p2"
                          name="P2 缺陷"
                          stroke={chartColors.chart1}
                          strokeWidth={2}
                          dot={{ r: 4 }}
                        />
                      </LineChart>
                    </ResponsiveContainer>
                  </CardContent>
                </Card>
              </div>
            </div>
          )
        }}
      </AsyncState>

      {isError && (!data || data.items?.length === 0) ? (
        <ErrorState error={error} onRetry={refetch} />
      ) : (
      <DataTable
        columns={reportColumns}
        data={items}
        rowKey={(r) => r.id}
        loading={isLoading || isRefetching}
        loadingRows={4}
        emptyState={{ title: '暂无报告', description: '选择测试计划生成第一份报告' }}
        pagination={{
          page: data?.page || 1,
          totalPages,
          total: data?.total || 0,
          onChange: (p) => setPage(p),
        }}
        toolbar={
          <div className="flex items-center gap-2 flex-wrap">
            <Input
              placeholder="搜索报告名称"
              className="w-[220px]"
              value={keyword}
              onChange={(e) => setKeyword(e.target.value)}
              onKeyDown={handleKeyDown}
            />
            <Button variant="outline" size="sm" onClick={handleSearch} data-icon="inline-start">
              <Search />
              搜索
            </Button>
            <Button size="sm" onClick={openCreate} data-icon="inline-start">
              <Plus />
              生成报告
            </Button>
          </div>
        }
      />
      )}

      {/* Create Dialog */}
      <Dialog open={createOpen} onOpenChange={(open) => { if (!open) setCreateOpen(false) }}>
        <DialogContent className="sm:max-w-[500px]">
          <DialogHeader>
            <DialogTitle>生成报告</DialogTitle>
            <DialogDescription>选择测试计划并填写报告信息</DialogDescription>
          </DialogHeader>
          <form onSubmit={handleSubmit(doCreate)} className="flex flex-col gap-4">
            <div className="flex flex-col gap-1.5" data-invalid={!!errors.plan_id} aria-invalid={!!errors.plan_id}>
              <label className="text-sm font-medium">选择计划</label>
              <Select
                value={watchPlanId ? String(watchPlanId) : undefined}
                onValueChange={(v) => setValue('plan_id', Number(v), { shouldValidate: true })}
              >
                <SelectTrigger className={cn(errors.plan_id && 'border-destructive')}>
                  <SelectValue placeholder="选择测试计划" />
                </SelectTrigger>
                <SelectContent>
                  {plans.map((p: any) => (
                    <SelectItem key={p.id} value={String(p.id)}>
                      {p.plan_id || ''} {p.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {errors.plan_id && <span className="text-xs text-destructive">{errors.plan_id.message}</span>}
            </div>
            <div className="flex flex-col gap-1.5" data-invalid={!!errors.name} aria-invalid={!!errors.name}>
              <label className="text-sm font-medium">报告名称</label>
              <Input
                placeholder="如：v1.0 回归测试报告"
                {...register('name')}
                className={cn(errors.name && 'border-destructive')}
              />
              {errors.name && <span className="text-xs text-destructive">{errors.name.message}</span>}
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium">模板 ID <span className="text-muted-foreground font-normal">(可选)</span></label>
              <Input
                type="number"
                placeholder="关联的报告模板 ID，留空则使用默认模板"
                {...register('template_id')}
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium">备注</label>
              <Textarea placeholder="可选" rows={2} {...register('description')} />
            </div>
          </form>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCreateOpen(false)}>取消</Button>
            <Button disabled={creating} onClick={() => handleSubmit(doCreate)()} data-icon="inline-start">
              {creating && <Loader2 className="animate-spin" />}
              生成
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Detail Sheet */}
      <Sheet open={detailId !== null} onOpenChange={(open) => { if (!open) { setDetailId(null); setDetail(null) } }}>
        <SheetContent side="right" className="w-[820px] sm:max-w-[820px] overflow-y-auto">
          <SheetHeader>
            <SheetTitle>报告: {detail?.name || ''}</SheetTitle>
            <SheetDescription>查看报告详细信息</SheetDescription>
          </SheetHeader>

          {detail && content ? (
            <div className="py-4 flex flex-col gap-4">
              {/* Descriptions */}
              <dl className="grid grid-cols-2 gap-3 text-sm">
                <div className="flex flex-col gap-0.5">
                  <dt className="text-xs text-muted-foreground">编号</dt>
                  <dd>{detail.report_id}</dd>
                </div>
                <div className="flex flex-col gap-0.5">
                  <dt className="text-xs text-muted-foreground">关联计划</dt>
                  <dd>{detail.plan_name}</dd>
                </div>
                <div className="flex flex-col gap-0.5">
                  <dt className="text-xs text-muted-foreground">生成时间</dt>
                  <dd>{detail.created_at ? new Date(detail.created_at).toLocaleString() : '-'}</dd>
                </div>
                <div className="flex flex-col gap-0.5">
                  <dt className="text-xs text-muted-foreground">快照时间</dt>
                  <dd>{content.generated_at ? new Date(content.generated_at).toLocaleString() : '-'}</dd>
                </div>
                {detail.description && (
                  <div className="flex flex-col gap-0.5 col-span-2">
                    <dt className="text-xs text-muted-foreground">备注</dt>
                    <dd>{detail.description}</dd>
                  </div>
                )}
              </dl>

              {/* Quality Gate */}
              {detail.gate_status && (
                <div className="flex items-center gap-2 rounded-md border p-3">
                  <span className="text-sm font-medium">质量门禁：</span>
                  <Badge variant={
                    detail.gate_status === 'pass' ? 'default'
                      : detail.gate_status === 'fail' ? 'destructive'
                      : 'secondary'
                  }>
                    {detail.gate_status === 'pass' ? '✅ 通过' : detail.gate_status === 'fail' ? '❌ 未通过' : '⚠️ 警告'}
                  </Badge>
                  {detail.gate_details && detail.gate_details.length > 0 && (
                    <div className="ml-2 text-xs text-muted-foreground">
                      {detail.gate_details.map((d: string, i: number) => (
                        <div key={i}>{d}</div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* Export button */}
              <div className="flex justify-end">
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="outline" size="sm" data-icon="inline-start">
                      <Download />
                      导出
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                    <DropdownMenuItem onClick={() => window.open(exportReportUrl(detail.id, 'csv'), '_blank')}>
                      <FileDown />
                      CSV
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={() => window.open(exportReportUrl(detail.id, 'excel'), '_blank')}>
                      <FileSpreadsheet />
                      Excel
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={() => window.open(exportReportUrl(detail.id, 'pdf'), '_blank')}>
                      <FileText />
                      PDF
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </div>

              {/* Stats grid */}
              <div className="grid grid-cols-10 gap-2">
                {/* Total count */}
                <div className="col-span-2">
                  <Card size="sm" className="text-center">
                    <CardContent className="py-2 px-2">
                      <div className="text-xs text-muted-foreground">总用例</div>
                      <div className="text-2xl font-bold">{dStats.total || 0}</div>
                    </CardContent>
                  </Card>
                </div>
                {/* Pass rate */}
                <div className="col-span-2">
                  <Card size="sm">
                    <CardContent className="py-2 px-3">
                      <Progress value={dPassRate} className="h-2" />
                      <div className="text-xs text-muted-foreground mt-1 text-center">{dPassRate}% 通过率</div>
                    </CardContent>
                  </Card>
                </div>
                {/* Status counts */}
                {statItems.map((item) => (
                  <div key={item.key} className="col-span-1">
                    <Card size="sm" className="text-center">
                      <CardContent className="py-2 px-1">
                        <div className="text-lg font-bold" style={{ color: item.color }}>{item.value}</div>
                        <div className="text-[10px] text-muted-foreground">{item.key}</div>
                      </CardContent>
                    </Card>
                  </div>
                ))}
              </div>

              {/* Case List */}
              <Card size="sm">
                <CardHeader>
                  <CardTitle>用例明细 ({dCases.length})</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="rounded-xl border bg-card text-sm -mx-[var(--card-spacing)]">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>标题</TableHead>
                          <TableHead className="w-[100px]">模块</TableHead>
                          <TableHead className="w-[80px]">结果</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {dCases.map((c: any) => {
                          const st = STATUS_CONFIG[c.last_status] || STATUS_CONFIG.pending
                          const StatusIcon = st.icon
                          return (
                            <TableRow key={c.case_id}>
                              <TableCell className="truncate">
                                <div className="flex items-center gap-1.5">
                                  <Badge variant={PRIORITY_CONFIG[c.priority] || 'default'} className="shrink-0">
                                    {c.priority}
                                  </Badge>
                                  <span className="text-xs text-muted-foreground shrink-0">{c.case_id_code}</span>
                                  <span className="truncate">{c.title}</span>
                                </div>
                              </TableCell>
                              <TableCell className="max-w-[100px] truncate">{c.module}</TableCell>
                              <TableCell>
                                <Badge variant={st.variant}>
                                  <StatusIcon className={cn('size-3', st.color)} />
                                  <span className="ml-0.5">{st.label}</span>
                                </Badge>
                              </TableCell>
                            </TableRow>
                          )
                        })}
                      </TableBody>
                    </Table>
                  </div>
                </CardContent>
              </Card>
            </div>
          ) : (
            <div className="py-4">
              <SkeletonText lines={6} />
            </div>
          )}
        </SheetContent>
      </Sheet>
    </div>
  )
}
