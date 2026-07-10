import { useCallback, useEffect, useState } from 'react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import {
  fetchWikiConfig, fetchWikiRawSources, fetchWikiPages, fetchWikiPage,
  fetchWikiPageLinks, createWikiIngestJob, approveWikiPage, rejectWikiPage,
} from '@/api/wiki'
import type { WikiConfig, WikiRawSource, WikiPageBrief, WikiPage, WikiLink } from '@/types'
import { useAuthStore } from '@/stores/auth'
import { Upload, RefreshCw, Loader2, BookOpen, CheckCircle2, FileText } from '@/lib/icons'
import WikiImportDialog from './WikiImportDialog'

const PAGE_TYPE_LABEL: Record<string, string> = {
  source: '来源', module: '模块', requirement: '需求', rule: '规则',
  api: '接口', entity: '实体', comparison: '对比', query: '查询',
  overview: '总览', index: '索引', log: '日志',
}
const REVIEW_VARIANT: Record<string, 'default' | 'secondary' | 'destructive' | 'outline'> = {
  approved: 'default', pending: 'secondary', rejected: 'destructive', draft: 'outline',
}

export default function WikiTab() {
  const hasPerm = useAuthStore((s) => s.hasPerm)
  const [config, setConfig] = useState<WikiConfig | null>(null)
  const [raws, setRaws] = useState<WikiRawSource[]>([])
  const [pages, setPages] = useState<WikiPageBrief[]>([])
  const [loading, setLoading] = useState(false)
  const [importOpen, setImportOpen] = useState(false)
  const [compiling, setCompiling] = useState<number | null>(null)
  const [selected, setSelected] = useState<WikiPage | null>(null)
  const [links, setLinks] = useState<WikiLink[]>([])
  const [detailLoading, setDetailLoading] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [cfg, rawPage, pagePage] = await Promise.all([
        fetchWikiConfig().catch(() => null),
        fetchWikiRawSources({ page: 1, page_size: 50 }).catch(() => null),
        fetchWikiPages({ page: 1, page_size: 200 }).catch(() => null),
      ])
      if (cfg) setConfig(cfg)
      if (rawPage) setRaws(rawPage.items || [])
      if (pagePage) setPages(pagePage.items || [])
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
      toast.success(`已提交 Wiki 编译任务 #${job.id}，稍后刷新查看页面`)
      setTimeout(() => load(), 1500)
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
  const grouped = pages.reduce<Record<string, WikiPageBrief[]>>((acc, p) => {
    (acc[p.page_type] ||= []).push(p); return acc
  }, {})

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <div className="flex items-center gap-1.5 text-sm font-medium">
          <BookOpen className="size-4" /> Wiki 知识库
          {config && !config.wiki_enabled && (
            <Badge variant="outline" className="text-amber-600 border-amber-300">未启用</Badge>
          )}
        </div>
        <span className="ml-2 text-xs text-muted-foreground">来源 {raws.length} · 页面 {pages.length}</span>
        <div className="ml-auto flex items-center gap-2">
          <Button variant="outline" size="sm" className="h-8" onClick={load} disabled={loading}>
            {loading ? <Loader2 className="size-4 animate-spin" /> : <RefreshCw className="size-4" />}
          </Button>
          {canManage && (
            <Button size="sm" className="h-8" onClick={() => setImportOpen(true)}>
              <Upload className="size-4 mr-1" /> 导入蓝湖
            </Button>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[320px_1fr] gap-3">
        {/* 左：来源 + Wiki 页面树 */}
        <div className="space-y-3">
          <Card>
            <CardContent className="p-3 space-y-2">
              <div className="text-xs font-medium text-muted-foreground">原始来源</div>
              {loading ? <Skeleton className="h-10 w-full" /> : raws.length === 0 ? (
                <div className="text-xs text-muted-foreground py-2">暂无来源，先导入蓝湖需求</div>
              ) : raws.map((r) => (
                <div key={r.id} className="flex items-center gap-2 text-sm">
                  <span className="truncate flex-1" title={r.title}>{r.title || '(无标题)'}</span>
                  <Badge variant={r.status === 'active' ? 'secondary' : 'outline'} className="shrink-0">{r.status}</Badge>
                  {canManage && (
                    <Button variant="ghost" size="sm" className="h-6 px-2 text-xs shrink-0"
                      disabled={compiling === r.id} onClick={() => compile(r.id)}>
                      {compiling === r.id ? <Loader2 className="size-3 animate-spin" /> : '编译'}
                    </Button>
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
                  <div className="text-[11px] text-muted-foreground mt-1">{PAGE_TYPE_LABEL[type] || type}</div>
                  {grouped[type].map((p) => (
                    <button key={p.id}
                      onClick={() => openPage(p.id)}
                      className={`w-full flex items-center gap-1.5 text-left text-sm px-2 py-1 rounded hover:bg-muted ${
                        selected?.id === p.id ? 'bg-muted' : ''}`}>
                      <FileText className="size-3.5 text-muted-foreground shrink-0" />
                      <span className="truncate flex-1">{p.title}</span>
                      <Badge variant={REVIEW_VARIANT[p.review_status] ?? 'outline'} className="shrink-0 text-[10px]">
                        {p.review_status}
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
                  <Badge variant="secondary">{PAGE_TYPE_LABEL[selected.page_type] || selected.page_type}</Badge>
                  <Badge variant={REVIEW_VARIANT[selected.review_status] ?? 'outline'}>{selected.review_status}</Badge>
                  <span className="text-xs text-muted-foreground">v{selected.version}</span>
                  {canApprove && selected.review_status !== 'approved' && (
                    <div className="ml-auto flex gap-1.5">
                      <Button size="sm" variant="outline" className="h-7" onClick={() => review(false)}>驳回</Button>
                      <Button size="sm" className="h-7" onClick={() => review(true)}>
                        <CheckCircle2 className="size-3.5 mr-1" /> 通过
                      </Button>
                    </div>
                  )}
                </div>
                <pre className="whitespace-pre-wrap text-xs bg-muted/40 rounded-md p-3 max-h-[420px] overflow-auto font-mono leading-relaxed">
                  {selected.content_md}
                </pre>
                <div className="text-xs text-muted-foreground">
                  来源引用：<span className="font-mono break-all">{selected.source_refs_json}</span>
                </div>
                {links.length > 0 && (
                  <div className="text-xs text-muted-foreground">
                    关联页面：{links.map((l) => (
                      <Badge key={l.id} variant="outline" className="mr-1">
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
