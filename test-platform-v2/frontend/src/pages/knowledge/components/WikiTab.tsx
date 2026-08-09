import { useCallback, useEffect, useState } from 'react'
import { toast } from 'sonner'
import { Button } from '@/ui'
import { Badge } from '@/ui'
import { Card, CardContent } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import {
  fetchWikiConfig, fetchWikiRawSources, fetchWikiPages, fetchWikiPage,
  fetchWikiPageLinks, fetchWikiRawSource, createWikiIngestJob, fetchWikiIngestJob, approveWikiPage, rejectWikiPage,
  fetchWikiSyncAvailability, syncBundleToWiki,
} from '@/api/wiki'
import type {
  WikiConfig,
  WikiIngestJob,
  WikiLink,
  WikiPage,
  WikiPageBrief,
  WikiRawSource,
  WikiSyncAvailability,
} from '@/types'
import { useAuthStore } from '@/stores/auth'
import { Upload, RefreshCw, Loader2, BookOpen, CheckCircle2, FileText, ExternalLink, GitBranch, Layers } from '@/lib/icons'
import WikiImportDialog from './WikiImportDialog'
import { reviewStatusLabel, sourceStatusLabel } from './knowledgeStatus'

const PAGE_TYPE_LABEL: Record<string, string> = {
  source: '来源', module: '模块', requirement: '需求', rule: '规则',
  api: '接口', entity: '实体', comparison: '对比', query: '查询',
  overview: '总览', index: '索引', log: '日志',
}
const REVIEW_TONE: Record<string, 'success' | 'warning' | 'danger' | 'info' | 'neutral'> = {
  approved: 'success', pending: 'neutral', rejected: 'danger', draft: 'neutral',
}

export default function WikiTab() {
  const hasPerm = useAuthStore((s) => s.hasPerm)
  const [config, setConfig] = useState<WikiConfig | null>(null)
  const [raws, setRaws] = useState<WikiRawSource[]>([])
  const [pages, setPages] = useState<WikiPageBrief[]>([])
  const [loading, setLoading] = useState(false)
  const [syncAvailability, setSyncAvailability] = useState<WikiSyncAvailability | null>(null)
  const [syncing, setSyncing] = useState(false)
  const [importOpen, setImportOpen] = useState(false)
  const [compiling, setCompiling] = useState<number | null>(null)
  const [activeJob, setActiveJob] = useState<WikiIngestJob | null>(null)
  const [jobOpen, setJobOpen] = useState(false)
  const [selected, setSelected] = useState<WikiPage | null>(null)
  const [links, setLinks] = useState<WikiLink[]>([])
  const [detailLoading, setDetailLoading] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [cfg, rawPage, pagePage, availability] = await Promise.all([
        fetchWikiConfig().catch(() => null),
        fetchWikiRawSources({ page: 1, page_size: 50 }).catch(() => null),
        fetchWikiPages({ page: 1, page_size: 200 }).catch(() => null),
        fetchWikiSyncAvailability().catch(() => ({
          available: false,
          reason: '无法读取 Wiki 同步前置条件，请稍后重试。',
          release_bundle_id: null,
          release_bundle_name: '',
          release_bundle_status: '',
        })),
      ])
      if (cfg) setConfig(cfg)
      if (rawPage) setRaws(rawPage.items || [])
      if (pagePage) setPages(pagePage.items || [])
      setSyncAvailability(availability)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const openPage = async (id: number) => {
    setDetailLoading(true)
    try {
      const [p, ls] = await Promise.all([fetchWikiPage(id), fetchWikiPageLinks(id).catch(() => [])])
      setSelected(p); setLinks(ls)
    } catch (e: any) {
      toast.error(e?.message || '加载页面失败')
    } finally {
      setDetailLoading(false)
    }
  }

  const compile = async (rawId: number) => {
    setCompiling(rawId)
    try {
      const job = await createWikiIngestJob(rawId)
      setActiveJob(job)
      setJobOpen(true)
      toast.success(`已提交 Wiki 编译任务 #${job.id}，完成后自动刷新页面`)
      let current = job
      for (let i = 0; i < 60 && current.status !== 'success' && current.status !== 'failed'; i += 1) {
        await new Promise((resolve) => setTimeout(resolve, 1500))
        current = await fetchWikiIngestJob(job.id).catch(() => current)
        setActiveJob(current)
      }
      if (current.status === 'success') {
        await load()
        toast.success('Wiki 编译完成，已生成页面（可在左侧打开查看内容）')
        try {
          const paged = await fetchWikiPages({ page_size: 50 })
          const first = (paged.items || [])[0]
          if (first) await openPage(first.id)
        } catch { /* 自动打开失败可忽略 */ }
      } else if (current.status === 'failed') {
        toast.error(current.error_message || `Wiki 编译任务 #${job.id} 失败`)
      }
    } catch (e: any) {
      toast.error(e?.message || '触发编译失败')
    } finally {
      setCompiling(null)
    }
  }

  const review = async (approve: boolean) => {
    if (!selected) return
    try {
      const updated = approve ? await approveWikiPage(selected.id) : await rejectWikiPage(selected.id)
      setSelected(updated)
      setPages((ps) => ps.map((p) => (p.id === updated.id ? { ...p, review_status: updated.review_status } : p)))
      toast.success(approve ? '已通过' : '已驳回')
    } catch (e: any) {
      toast.error(e?.message || '操作失败')
    }
  }

  const canManage = hasPerm('wiki:manage')
  const canApprove = hasPerm('wiki:approve')
  const syncUnavailableReason = !canManage
    ? '当前账号缺少 Wiki 管理权限，无法同步发布包。'
    : syncAvailability && !syncAvailability.available
      ? syncAvailability.reason
      : ''

  const syncReleaseBundle = async () => {
    if (!canManage || !syncAvailability?.available || !syncAvailability.release_bundle_id) return
    setSyncing(true)
    try {
      const result = await syncBundleToWiki(syncAvailability.release_bundle_id)
      toast.success(
        `Wiki 同步完成：新增 ${result.raw_sources_created}，更新 ${result.raw_sources_updated}，跳过 ${result.raw_sources_skipped}`,
      )
      await load()
    } catch (e: any) {
      toast.error(e?.message || 'Wiki 同步失败')
    } finally {
      setSyncing(false)
    }
  }

  const grouped = pages.reduce<Record<string, WikiPageBrief[]>>((acc, p) => {
    (acc[p.page_type] ||= []).push(p); return acc
  }, {})

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <div className="flex items-center gap-1.5 text-sm font-medium">
          <BookOpen className="size-4" /> Wiki 知识库
          {config && !config.wiki_enabled && (
            <Badge tone="neutral" className="text-status-warning dark:text-status-warning border-status-warning-border dark:border-status-warning-border">未启用</Badge>
          )}
        </div>
        <span className="ml-2 text-xs text-muted-foreground">来源 {raws.length} · 页面 {pages.length}</span>
        <div className="ml-auto flex items-center gap-2">
          <Button
            variant="secondary"
            size="sm"
            className="h-8"
            aria-label="同步发布包到 Wiki"
            title={syncAvailability?.release_bundle_name || syncUnavailableReason}
            onClick={syncReleaseBundle}
            disabled={
              loading
              || syncing
              || !canManage
              || !syncAvailability?.available
              || !syncAvailability.release_bundle_id
            }
          >
            {syncing ? <Loader2 className="size-4 animate-spin" /> : <GitBranch className="size-4" />}
            同步发布包
          </Button>
          <Button variant="secondary" size="sm" className="h-8" onClick={load} disabled={loading}>
            {loading ? <Loader2 className="size-4 animate-spin" /> : <RefreshCw className="size-4" />}
          </Button>
          {canManage && (
            <Button size="sm" className="h-8" onClick={() => setImportOpen(true)}>
              <Upload className="size-4 mr-1" /> 导入蓝湖
            </Button>
          )}
        </div>
      </div>

      {activeJob && jobOpen && (
        <div role="status" className="rounded-md border p-3 space-y-2 text-sm">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-medium">Wiki 编译任务 #{activeJob.id}</span>
            {(activeJob.status === 'running' || activeJob.status === 'pending' || activeJob.status === 'queued') ? (
              <Badge tone="neutral" className="gap-1">
                <Loader2 className="size-3 animate-spin" aria-hidden="true" /> 进行中（{activeJob.stage}）
              </Badge>
            ) : activeJob.status === 'success' ? (
              <Badge tone="success">成功</Badge>
            ) : activeJob.status === 'failed' ? (
              <Badge tone="danger">失败</Badge>
            ) : (
              <Badge tone="neutral">{activeJob.status}</Badge>
            )}
            {activeJob.finished_at && (
              <span className="text-xs text-muted-foreground">完成于 {activeJob.finished_at.slice(0, 19).replace('T', ' ')}</span>
            )}
            <Button variant="ghost" size="sm" className="h-6 ml-auto" onClick={() => setJobOpen(false)}>关闭</Button>
          </div>
          {activeJob.stage && activeJob.status !== 'success' && activeJob.status !== 'failed' && (
            <div className="text-xs text-muted-foreground">阶段：{activeJob.stage}（编译进行中，完成后自动刷新并展示页面）</div>
          )}
          {activeJob.error_message && (
            <div className="text-xs text-status-danger">{activeJob.error_message}</div>
          )}
          {activeJob.status === 'failed' && (
            <div className="text-xs text-muted-foreground">可在左侧来源列表重新点击「编译」重试。</div>
          )}
        </div>
      )}

      {syncUnavailableReason && (
        <div
          role="status"
          className="flex flex-wrap items-center gap-x-2 gap-y-1 rounded-md border border-status-warning-border bg-status-warning-muted px-3 py-2 text-xs text-status-warning"
        >
          <span>{syncUnavailableReason}</span>
          {canManage && (
            <a href="/release-bundles" className="font-medium underline underline-offset-2">
              前往发布包管理
            </a>
          )}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-[320px_1fr] gap-3">
        {/* 左：来源 + Wiki 页面树 */}
        <div className="space-y-3">
          <Card>
            <CardContent className="p-3 space-y-2">
              <div className="text-xs font-medium text-muted-foreground">原始来源</div>
              {loading ? <Skeleton className="h-10 w-full" /> : raws.length === 0 ? (
                <div className="text-xs text-muted-foreground py-2">暂无来源，先导入蓝湖需求</div>
              ) : raws.map((r) => (
                <div key={r.id} className="space-y-1.5 text-sm py-1 border-b last:border-0 border-border/40">
                  <div className="flex items-center gap-2">
                    <span className="truncate flex-1 font-medium" title={r.title}>{r.title || '(无标题)'}</span>
                    <Badge tone={r.status === 'active' ? 'success' : 'neutral'} className="shrink-0 text-xs">{sourceStatusLabel(r.status)}</Badge>
                    {canManage && (
                      <Button variant="ghost" size="sm" className="h-6 px-2 text-xs shrink-0"
                        disabled={compiling === r.id} onClick={() => compile(r.id)}>
                        {compiling === r.id ? <Loader2 className="size-3 animate-spin" /> : '编译'}
                      </Button>
                    )}
                  </div>
                  {r.source_type === 'lanhu' && (
                    <div className="text-xs text-muted-foreground space-y-0.5">
                      {r.immutable_version && (
                        <div className="flex items-center gap-1">
                          <GitBranch className="size-3 shrink-0" />
                          <span className="font-mono truncate" title={r.immutable_version}>{r.immutable_version}</span>
                        </div>
                      )}
                      <div className="flex flex-wrap gap-1">
                        {r.doc_id && <Badge tone="neutral" className="text-xs h-4 px-1 font-mono">docId:{r.doc_id.slice(0,12)}...</Badge>}
                        {r.version_id && <Badge tone="neutral" className="text-xs h-4 px-1 font-mono">ver:{r.version_id.slice(0,8)}...</Badge>}
                        {r.page_id && <Badge tone="neutral" className="text-xs h-4 px-1 font-mono">page:{r.page_id.slice(0,8)}...</Badge>}
                      </div>
                      {r.source_ref && (
                        <a href={r.source_ref} target="_blank" rel="noopener noreferrer"
                          className="flex items-center gap-0.5 text-status-info dark:text-status-info hover:underline truncate">
                          <ExternalLink className="size-3 shrink-0" />
                          <span className="truncate">蓝湖源链接</span>
                        </a>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-3 space-y-2">
              <div className="text-xs font-medium text-muted-foreground">Wiki 页面</div>
              {loading ? <Skeleton className="h-24 w-full" /> : pages.length === 0 ? (
                <div className="text-xs text-muted-foreground py-2">暂无页面，点击来源「编译」生成</div>
              ) : Object.keys(grouped).map((type) => (
                <div key={type} className="space-y-1">
                  <div className="text-xs text-muted-foreground mt-1">{PAGE_TYPE_LABEL[type] || type}</div>
                  {grouped[type].map((p) => (
                    <button key={p.id}
                      onClick={() => openPage(p.id)}
                      className={`w-full flex items-center gap-1.5 text-left text-sm px-2 py-1 rounded hover:bg-muted ${
                        selected?.id === p.id ? 'bg-muted' : ''}`}>
                      <FileText className="size-3.5 text-muted-foreground shrink-0" />
                      <span className="truncate flex-1">{p.title}</span>
                      <Badge tone={REVIEW_TONE[p.review_status] ?? 'neutral'} className="shrink-0 text-xs">
                        {reviewStatusLabel(p.review_status)}
                      </Badge>
                    </button>
                  ))}
                </div>
              ))}
            </CardContent>
          </Card>
        </div>

        {/* 右：页面预览 + 审核 */}
        <Card className="min-h-[360px]">
          <CardContent className="p-4">
            {detailLoading ? (
              <div className="h-40 flex items-center justify-center">
                <Loader2 className="size-5 animate-spin text-muted-foreground" />
              </div>
            ) : !selected ? (
              <div className="h-40 flex items-center justify-center text-sm text-muted-foreground">
                选择左侧 Wiki 页面查看内容与来源引用
              </div>
            ) : (
              <div className="space-y-3">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="font-medium">{selected.title}</span>
                  <Badge tone="neutral">{PAGE_TYPE_LABEL[selected.page_type] || selected.page_type}</Badge>
                  <Badge tone={REVIEW_TONE[selected.review_status] ?? 'neutral'}>{reviewStatusLabel(selected.review_status)}</Badge>
                  <span className="text-xs text-muted-foreground">v{selected.version}</span>
                  {canApprove && selected.review_status !== 'approved' && (
                    <div className="ml-auto flex gap-1.5">
                      <Button size="sm" variant="secondary" className="h-7" onClick={() => review(false)}>驳回</Button>
                      <Button size="sm" className="h-7" onClick={() => review(true)}>
                        <CheckCircle2 className="size-3.5 mr-1" /> 通过
                      </Button>
                    </div>
                  )}
                </div>
                <pre className="whitespace-pre-wrap text-xs bg-muted/40 rounded-md p-3 max-h-[420px] overflow-auto font-mono leading-relaxed">
                  {selected.content_md}
                </pre>
                {/* Raw Source → Wiki Page 追溯 */}
                {(() => {
                  try {
                    const refs = JSON.parse(selected.source_refs_json || '[]')
                    if (refs.length === 0) return null
                    return (
                      <div className="text-xs text-muted-foreground space-y-1">
                        <div className="font-medium flex items-center gap-1">
                          <Layers className="size-3" /> 来源追溯
                        </div>
                        {refs.map((ref: any, i: number) => (
                          <div key={i} className="flex items-center gap-1.5 ml-1">
                            {ref.raw_source_id && (
                              <Badge tone="neutral" className="text-xs font-mono">
                                Raw Source #{ref.raw_source_id}
                              </Badge>
                            )}
                            {ref.knowledge_source_id && (
                              <Badge tone="neutral" className="text-xs font-mono">
                                知识源 #{ref.knowledge_source_id}
                              </Badge>
                            )}
                            {ref.raw_source_id && (
                              <button
                                className="text-status-info dark:text-status-info hover:underline text-xs"
                                onClick={async () => {
                                  try {
                                    const raw = await fetchWikiRawSource(ref.raw_source_id)
                                    if (raw?.immutable_version) {
                                      const el = document.getElementById('wiki-raw-version')
                                      if (el) el.textContent = raw.immutable_version
                                    }
                                  } catch { /* ignore */ }
                                }}
                              >
                                查看来源
                              </button>
                            )}
                          </div>
                        ))}
                      </div>
                    )
                  } catch { return null }
                })()}
                <div className="text-xs text-muted-foreground">
                  来源引用：<span className="font-mono break-all">{selected.source_refs_json}</span>
                </div>
                {links.length > 0 && (
                  <div className="text-xs text-muted-foreground">
                    关联页面：{links.map((l) => (
                      <Badge key={l.id} tone="neutral" className="mr-1">
                        {l.link_type} #{l.from_page_id === selected.id ? l.to_page_id : l.from_page_id}
                      </Badge>
                    ))}
                  </div>
                )}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <WikiImportDialog open={importOpen} onOpenChange={setImportOpen} onImported={() => load()} />
    </div>
  )
}
