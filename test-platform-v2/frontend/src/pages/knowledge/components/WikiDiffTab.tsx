import { useCallback, useEffect, useState } from 'react'
import { toast } from 'sonner'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select'
import {
  createWikiDiffTask, fetchWikiDiffTasks, fetchWikiDiffTask,
} from '@/api/wiki'
import type { WikiConfig, WikiDiffTask, WikiDiffTaskBrief, WikiDiffItem } from '@/types'
import { fetchWikiConfig } from '@/api/wiki'
import { useAuthStore } from '@/stores/auth'
import { GitCompare, Loader2, ArrowLeftRight } from '@/lib/icons'
import WikiDiffDetailDrawer from './WikiDiffDetailDrawer'

const KB_OPTIONS = [
  { v: 'platform_rag', l: '平台 RAG 知识库' },
  { v: 'platform_wiki', l: 'LLM Wiki 知识库' },
]
const SEVERITY_VARIANT: Record<string, 'default' | 'secondary' | 'destructive' | 'outline'> = {
  P0: 'destructive', P1: 'destructive', P2: 'secondary', P3: 'outline',
}

function ContractView({ title, json }: { title: string; json: any }) {
  return (
    <Card>
      <CardContent className="p-3">
        <div className="text-xs font-medium text-muted-foreground mb-1">{title}</div>
        <pre className="whitespace-pre-wrap text-[11px] bg-muted/40 rounded p-2 max-h-[360px] overflow-auto font-mono">
          {json ? JSON.stringify(json, null, 2) : '（暂无）'}
        </pre>
      </CardContent>
    </Card>
  )
}

export default function WikiDiffTab() {
  const hasPerm = useAuthStore((s) => s.hasPerm)
  const [config, setConfig] = useState<WikiConfig | null>(null)
  const [query, setQuery] = useState(() => new URLSearchParams(window.location.search).get('q') || '')
  const [leftKb, setLeftKb] = useState('platform_rag')
  const [rightKb, setRightKb] = useState('platform_wiki')
  const [running, setRunning] = useState(false)
  const [tasks, setTasks] = useState<WikiDiffTaskBrief[]>([])
  const [task, setTask] = useState<WikiDiffTask | null>(null)
  const [sevFilter, setSevFilter] = useState<string>('all')
  const [dimFilter, setDimFilter] = useState<string>('all')
  const [active, setActive] = useState<WikiDiffItem | null>(null)

  const loadTasks = useCallback(async () => {
    const [cfg, page] = await Promise.all([
      fetchWikiConfig().catch(() => null),
      fetchWikiDiffTasks({ page: 1, page_size: 30 }).catch(() => null),
    ])
    if (cfg) setConfig(cfg)
    if (page) setTasks(page.items || [])
  }, [])

  useEffect(() => { loadTasks() }, [loadTasks])

  const openTask = useCallback(async (id: number) => {
    const filters: Record<string, string> = {}
    if (sevFilter !== 'all') filters.severity = sevFilter
    if (dimFilter !== 'all') filters.dimension = dimFilter
    const t = await fetchWikiDiffTask(id, filters).catch(() => null)
    if (t) setTask(t)
  }, [sevFilter, dimFilter])

  useEffect(() => { if (task) openTask(task.id) /* eslint-disable-next-line */ }, [sevFilter, dimFilter])

  const run = async () => {
    const q = query.trim()
    if (!q) return
    setRunning(true)
    try {
      const created = await createWikiDiffTask({ query: q, left_kb_type: leftKb, right_kb_type: rightKb })
      toast.success(`已发起对比任务 #${created.id}`)
      // 轮询直到完成（后台执行）
      for (let i = 0; i < 8; i++) {
        await new Promise((r) => setTimeout(r, 1200))
        const t = await fetchWikiDiffTask(created.id).catch(() => null)
        if (t && (t.status === 'success' || t.status === 'failed')) { setTask(t); break }
        if (t) setTask(t)
      }
      loadTasks()
    } catch (e: any) {
      toast.error(e?.message || '发起对比失败（需启用 wiki_diff 且有 wiki:diff 权限）')
    } finally {
      setRunning(false)
    }
  }

  const summary = task?.summary_json ? JSON.parse(task.summary_json) : null
  const items = task?.items || []

  const onItemChanged = (updated: WikiDiffItem) => {
    setTask((t) => (t ? { ...t, items: t.items.map((i) => (i.id === updated.id ? updated : i)) } : t))
    setActive(updated)
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 flex-wrap">
        <div className="flex items-center gap-1.5 text-sm font-medium">
          <GitCompare className="size-4" /> 知识差异对比
          {config && !config.wiki_diff_enabled && (
            <Badge variant="outline" className="text-amber-600 border-amber-300">未启用</Badge>
          )}
        </div>
      </div>

      <div className="flex items-center gap-2 flex-wrap">
        <Input className="h-9 w-[240px]" placeholder="需求名/关键词（如：比赛推送）"
          value={query} onChange={(e) => setQuery(e.target.value)} />
        <Select value={leftKb} onValueChange={setLeftKb}>
          <SelectTrigger className="h-9 w-[170px] text-xs"><SelectValue /></SelectTrigger>
          <SelectContent>{KB_OPTIONS.map((o) => <SelectItem key={o.v} value={o.v}>{o.l}</SelectItem>)}</SelectContent>
        </Select>
        <ArrowLeftRight className="size-4 text-muted-foreground" />
        <Select value={rightKb} onValueChange={setRightKb}>
          <SelectTrigger className="h-9 w-[170px] text-xs"><SelectValue /></SelectTrigger>
          <SelectContent>{KB_OPTIONS.map((o) => <SelectItem key={o.v} value={o.v}>{o.l}</SelectItem>)}</SelectContent>
        </Select>
        <Button size="sm" className="h-9" disabled={running || !query.trim() || !hasPerm('wiki:diff')} onClick={run}>
          {running ? <Loader2 className="size-4 animate-spin mr-1" /> : null} 发起对比
        </Button>
        {tasks.length > 0 && (
          <Select value={task ? String(task.id) : ''} onValueChange={(v) => openTask(Number(v))}>
            <SelectTrigger className="h-9 w-[220px] text-xs ml-auto"><SelectValue placeholder="历史任务" /></SelectTrigger>
            <SelectContent>
              {tasks.map((t) => <SelectItem key={t.id} value={String(t.id)}>#{t.id} {t.title} · {t.status}</SelectItem>)}
            </SelectContent>
          </Select>
        )}
      </div>

      {!task ? (
        <div className="h-40 flex items-center justify-center text-sm text-muted-foreground">
          输入需求关键词并选择左右知识库，发起 RAG vs Wiki 差异对比
        </div>
      ) : task.status !== 'success' ? (
        <div className="h-40 flex items-center justify-center gap-2 text-sm text-muted-foreground">
          <Loader2 className="size-4 animate-spin" /> 任务 {task.status}…
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-[1fr_1.4fr_1fr] gap-3">
          <ContractView title="左侧契约（标准化）" json={summary?.left_contract} />

          <Card>
            <CardContent className="p-3 space-y-2">
              <div className="flex items-center gap-2">
                <span className="text-xs font-medium text-muted-foreground">差异 {items.length}</span>
                <Select value={sevFilter} onValueChange={setSevFilter}>
                  <SelectTrigger className="h-7 w-[90px] text-xs ml-auto"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">全部级别</SelectItem>
                    {['P0', 'P1', 'P2', 'P3'].map((s) => <SelectItem key={s} value={s}>{s}</SelectItem>)}
                  </SelectContent>
                </Select>
                <Select value={dimFilter} onValueChange={setDimFilter}>
                  <SelectTrigger className="h-7 w-[110px] text-xs"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">全部维度</SelectItem>
                    {['业务规则', '字段', '接口', '异常路径', '客户端', '测试覆盖', '验收标准', '需求范围'].map(
                      (d) => <SelectItem key={d} value={d}>{d}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              {items.length === 0 ? (
                <div className="text-center text-muted-foreground py-8 text-sm">未发现差异</div>
              ) : items.map((it) => (
                <button key={it.id} onClick={() => setActive(it)}
                  className="w-full text-left rounded-md border p-2 hover:bg-muted space-y-1">
                  <div className="flex items-center gap-1.5">
                    <Badge variant={SEVERITY_VARIANT[it.severity] ?? 'outline'} className="text-[10px]">{it.severity}</Badge>
                    <Badge variant="secondary" className="text-[10px]">{it.dimension}</Badge>
                    <Badge variant="outline" className="text-[10px]">{it.diff_type}</Badge>
                    {it.review_status !== 'pending' && (
                      <Badge variant="outline" className="text-[10px] ml-auto">{it.review_status}</Badge>
                    )}
                  </div>
                  <div className="text-sm truncate">{it.title}</div>
                </button>
              ))}
            </CardContent>
          </Card>

          <ContractView title="右侧契约（标准化）" json={summary?.right_contract} />
        </div>
      )}

      <WikiDiffDetailDrawer item={active} onOpenChange={(v) => { if (!v) setActive(null) }} onChanged={onItemChanged} />
    </div>
  )
}
