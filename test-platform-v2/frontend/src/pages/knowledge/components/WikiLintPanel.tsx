import { useCallback, useEffect, useState } from 'react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import {
  runWikiLint, fetchWikiLintReports, fetchWikiLintReport, convertWikiLintIssues,
} from '@/api/wiki'
import type { WikiLintReport, WikiLintReportBrief, WikiLintIssue } from '@/types'
import { useAuthStore } from '@/stores/auth'
import { ShieldCheck, RefreshCw, Loader2, Bug, ChevronRight, ArrowRight, AlertTriangle } from '@/lib/icons'

const RULE_LABEL: Record<string, string> = {
  orphan_page: '孤立页面',
  no_source: '无来源引用',
  stale_page: '过期页面',
  conflict_rule: '规则冲突',
  coverage_gap: '测试覆盖缺口',
}

const RULE_ICON: Record<string, string> = {
  orphan_page: 'LinkIcon',
  no_source: 'FileWarning',
  stale_page: 'GitBranch',
  conflict_rule: 'AlertTriangle',
  coverage_gap: 'ShieldCheck',
}

const SEVERITY_VARIANT: Record<string, 'destructive' | 'default' | 'secondary' | 'outline'> = {
  P0: 'destructive',
  P1: 'default',
  P2: 'secondary',
  P3: 'outline',
}

export default function WikiLintPanel() {
  const hasPerm = useAuthStore((s) => s.hasPerm)
  const [reports, setReports] = useState<WikiLintReportBrief[]>([])
  const [loading, setLoading] = useState(false)
  const [running, setRunning] = useState(false)
  const [selected, setSelected] = useState<WikiLintReport | null>(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [converting, setConverting] = useState<number[]>([])
  const [filters, setFilters] = useState<{ rule?: string; severity?: string; review_status?: string }>({})

  const loadReports = useCallback(async () => {
    setLoading(true)
    try {
      const page = await fetchWikiLintReports({ page: 1, page_size: 50 }).catch(() => null)
      if (page) setReports(page.items || [])
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { loadReports() }, [loadReports])

  const openReport = async (id: number) => {
    setDetailLoading(true)
    try {
      const r = await fetchWikiLintReport(id, filters)
      setSelected(r)
    } catch (e: any) {
      toast.error(e?.message || '加载报告失败')
    } finally {
      setDetailLoading(false)
    }
  }

  const runLint = async () => {
    setRunning(true)
    try {
      const report = await runWikiLint()
      toast.success(`Lint 扫描完成：共发现 ${report.issues?.length || 0} 个问题`)
      setSelected(report)
      await loadReports()
    } catch (e: any) {
      toast.error(e?.message || 'Lint 扫描失败')
    } finally {
      setRunning(false)
    }
  }

  const convertIssue = async (issueId: number) => {
    setConverting((prev) => [...prev, issueId])
    try {
      if (!selected) return
      const result = await convertWikiLintIssues(selected.id, { issue_ids: [issueId] })
      toast.success(`已转为待审产物 #${result.artifact_ids[0]}`)
      // 刷新报告
      const r = await fetchWikiLintReport(selected.id, filters)
      setSelected(r)
    } catch (e: any) {
      toast.error(e?.message || '转换失败')
    } finally {
      setConverting((prev) => prev.filter((id) => id !== issueId))
    }
  }

  const convertAll = async () => {
    if (!selected) return
    const pending = selected.issues.filter(
      (i) => i.review_status === 'pending' && !i.resolved_artifact_id,
    )
    if (pending.length === 0) {
      toast.info('没有可转换的问题')
      return
    }
    setConverting(pending.map((i) => i.id))
    try {
      const result = await convertWikiLintIssues(selected.id, { issue_ids: [] })
      toast.success(`已转换 ${result.converted} 个问题为待审产物`)
      const r = await fetchWikiLintReport(selected.id, filters)
      setSelected(r)
    } catch (e: any) {
      toast.error(e?.message || '批量转换失败')
    } finally {
      setConverting([])
    }
  }

  const canManage = hasPerm('wiki:manage')
  const canApprove = hasPerm('wiki:approve')

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <div className="flex items-center gap-1.5 text-sm font-medium">
          <ShieldCheck className="size-4" /> Wiki 健康体检
        </div>
        <span className="text-xs text-muted-foreground">报告 {reports.length}</span>
        <div className="ml-auto flex items-center gap-2">
          <Button variant="outline" size="sm" className="h-8" onClick={loadReports} disabled={loading}>
            {loading ? <Loader2 className="size-4 animate-spin" /> : <RefreshCw className="size-4" />}
          </Button>
          {canManage && (
            <Button size="sm" className="h-8" onClick={runLint} disabled={running}>
              {running ? (
                <Loader2 className="size-4 animate-spin mr-1" />
              ) : (
                <Bug className="size-4 mr-1" />
              )}
              {running ? '扫描中...' : '运行体检'}
            </Button>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[280px_1fr] gap-3">
        {/* 左侧：报告列表 */}
        <Card>
          <CardContent className="p-3 space-y-2">
            <div className="text-xs font-medium text-muted-foreground">历史报告</div>
            {loading ? (
              <Skeleton className="h-24 w-full" />
            ) : reports.length === 0 ? (
              <div className="text-xs text-muted-foreground py-4 text-center">
                暂无报告，点击「运行体检」开始
              </div>
            ) : (
              reports.map((r) => {
                const summary = (() => {
                  try { return JSON.parse(r.summary_json || '{}') } catch { return {} }
                })()
                const total = Object.values(summary).reduce(
                  (a: number, b: unknown) => a + (typeof b === 'number' ? b : 0), 0,
                ) as number
                return (
                  <button
                    key={r.id}
                    onClick={() => openReport(r.id)}
                    className={`w-full text-left px-2 py-2 rounded hover:bg-muted text-sm ${
                      selected?.id === r.id ? 'bg-muted' : ''
                    }`}
                  >
                    <div className="flex items-center gap-1.5">
                      <span className="text-xs text-muted-foreground font-mono">#{r.id}</span>
                      <Badge
                        variant={r.status === 'success' ? 'default' : r.status === 'failed' ? 'destructive' : 'secondary'}
                        className="text-[10px]"
                      >
                        {r.status}
                      </Badge>
                      <ChevronRight className="size-3 text-muted-foreground ml-auto" />
                    </div>
                    <div className="text-xs text-muted-foreground mt-0.5">
                      {total > 0 ? `${total} 个问题` : '无问题'}
                      {r.created_at && <span className="ml-2">{new Date(r.created_at).toLocaleDateString()}</span>}
                    </div>
                  </button>
                )
              })
            )}
          </CardContent>
        </Card>

        {/* 右侧：报告详情 + 问题列表 */}
        <Card className="min-h-[360px]">
          <CardContent className="p-4">
            {detailLoading ? (
              <div className="h-40 flex items-center justify-center">
                <Loader2 className="size-5 animate-spin text-muted-foreground" />
              </div>
            ) : !selected ? (
              <div className="h-40 flex items-center justify-center text-sm text-muted-foreground">
                选择左侧报告查看体检详情
              </div>
            ) : (
              <div className="space-y-3">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="font-medium">报告 #{selected.id}</span>
                  <Badge
                    variant={selected.status === 'success' ? 'default' : selected.status === 'failed' ? 'destructive' : 'secondary'}
                  >
                    {selected.status}
                  </Badge>
                  {selected.issues && (
                    <span className="text-xs text-muted-foreground">
                      {selected.issues.length} 个问题
                    </span>
                  )}
                  {canApprove && selected.issues?.some(
                    (i) => i.review_status === 'pending' && !i.resolved_artifact_id,
                  ) && (
                    <Button
                      size="sm" variant="outline" className="h-7 ml-auto"
                      onClick={convertAll}
                      disabled={converting.length > 0}
                    >
                      {converting.length > 0 ? (
                        <Loader2 className="size-3.5 animate-spin mr-1" />
                      ) : (
                        <ArrowRight className="size-3.5 mr-1" />
                      )}
                      全部转待审
                    </Button>
                  )}
                </div>

                {/* 筛选 */}
                {selected.issues && selected.issues.length > 0 && (
                  <div className="flex items-center gap-1.5 flex-wrap">
                    <span className="text-xs text-muted-foreground">筛选：</span>
                    {['', 'P0', 'P1', 'P2', 'P3'].map((s) => (
                      <Badge
                        key={s || 'all'}
                        variant={filters.severity === s || (!filters.severity && !s) ? 'default' : 'outline'}
                        className="text-[10px] cursor-pointer"
                        onClick={() => {
                          const next = { ...filters, severity: s || undefined }
                          setFilters(next)
                          openReport(selected.id)
                        }}
                      >
                        {s || '全部'}
                      </Badge>
                    ))}
                  </div>
                )}

                {/* 问题列表 */}
                {selected.status === 'failed' && selected.error_message && (
                  <div className="text-sm p-3 bg-red-50 dark:bg-red-950/30 rounded-md text-red-700 dark:text-red-300">
                    <AlertTriangle className="size-4 inline mr-1" />
                    {selected.error_message}
                  </div>
                )}

                {!selected.issues || selected.issues.length === 0 ? (
                  <div className="text-center py-8 text-sm text-muted-foreground">
                    <ShieldCheck className="size-8 mx-auto mb-2 text-green-500" />
                    未发现问题，Wiki 健康状态良好
                  </div>
                ) : (
                  <div className="space-y-2 max-h-[500px] overflow-auto">
                    {selected.issues.map((issue) => (
                      <div
                        key={issue.id}
                        className="border border-border rounded-md p-3 space-y-1.5"
                      >
                        <div className="flex items-center gap-1.5 flex-wrap">
                          <Badge variant="outline" className="text-[10px] font-mono">
                            {RULE_LABEL[issue.rule] || issue.rule}
                          </Badge>
                          <Badge variant={SEVERITY_VARIANT[issue.severity] ?? 'outline'} className="text-[10px]">
                            {issue.severity}
                          </Badge>
                          <Badge
                            variant={
                              issue.review_status === 'accepted' ? 'default' :
                              issue.review_status === 'rejected' ? 'destructive' :
                              'outline'
                            }
                            className="text-[10px]"
                          >
                            {issue.review_status}
                          </Badge>
                          {issue.resolved_artifact_id && (
                            <Badge variant="secondary" className="text-[10px] font-mono">
                              产物#{issue.resolved_artifact_id}
                            </Badge>
                          )}
                        </div>
                        <div className="text-sm font-medium">{issue.title}</div>
                        <div className="text-xs text-muted-foreground">{issue.description}</div>
                        {issue.suggestion && (
                          <div className="text-xs text-blue-600 dark:text-blue-400">
                            建议：{issue.suggestion}
                          </div>
                        )}
                        <div className="flex items-center gap-2 pt-1">
                          {issue.entity_type && issue.entity_id && (
                            <Badge variant="secondary" className="text-[10px] font-mono">
                              {issue.entity_type}#{issue.entity_id}
                            </Badge>
                          )}
                          {canApprove && issue.review_status === 'pending' && !issue.resolved_artifact_id && (
                            <Button
                              size="sm" variant="ghost" className="h-6 px-2 text-xs ml-auto"
                              disabled={converting.includes(issue.id)}
                              onClick={() => convertIssue(issue.id)}
                            >
                              {converting.includes(issue.id) ? (
                                <Loader2 className="size-3 animate-spin mr-1" />
                              ) : (
                                <ArrowRight className="size-3 mr-1" />
                              )}
                              转待审产物
                            </Button>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
