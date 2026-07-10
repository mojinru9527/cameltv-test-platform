import { useCallback, useEffect, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table'
import { Skeleton } from '@/components/ui/skeleton'
import { fetchWikiConfig, fetchWikiRawSources } from '@/api/wiki'
import type { WikiConfig, WikiRawSource } from '@/types'
import { useAuthStore } from '@/stores/auth'
import { Upload, RefreshCw, Loader2, BookOpen } from '@/lib/icons'
import WikiImportDialog from './WikiImportDialog'

const STATUS_VARIANT: Record<string, 'default' | 'secondary' | 'destructive' | 'outline'> = {
  active: 'default',
  superseded: 'secondary',
  deprecated: 'outline',
  failed: 'destructive',
}

export default function WikiTab() {
  const hasPerm = useAuthStore((s) => s.hasPerm)
  const [config, setConfig] = useState<WikiConfig | null>(null)
  const [rows, setRows] = useState<WikiRawSource[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [importOpen, setImportOpen] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [cfg, page] = await Promise.all([
        fetchWikiConfig().catch(() => null),
        fetchWikiRawSources({ page: 1, page_size: 50 }).catch(() => null),
      ])
      if (cfg) setConfig(cfg)
      if (page) { setRows(page.items || []); setTotal(page.total || 0) }
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const canManage = hasPerm('wiki:manage')

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <div className="flex items-center gap-1.5 text-sm font-medium">
          <BookOpen className="size-4" /> Wiki 知识库
          {config && !config.wiki_enabled && (
            <Badge variant="outline" className="text-amber-600 border-amber-300">未启用</Badge>
          )}
        </div>
        <span className="ml-2 text-xs text-muted-foreground">原始来源 {total}</span>
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

      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-[60px]">ID</TableHead>
              <TableHead>标题</TableHead>
              <TableHead className="w-[90px]">类型</TableHead>
              <TableHead className="w-[90px]">状态</TableHead>
              <TableHead className="w-[120px]">知识源</TableHead>
              <TableHead className="w-[160px]">更新时间</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading ? (
              Array.from({ length: 3 }).map((_, i) => (
                <TableRow key={i}>
                  <TableCell colSpan={6}><Skeleton className="h-5 w-full" /></TableCell>
                </TableRow>
              ))
            ) : rows.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} className="text-center text-muted-foreground py-8">
                  暂无原始来源{canManage ? '，点击「导入蓝湖」开始沉淀需求知识' : ''}
                </TableCell>
              </TableRow>
            ) : (
              rows.map((r) => (
                <TableRow key={r.id}>
                  <TableCell className="text-muted-foreground">{r.id}</TableCell>
                  <TableCell className="font-medium truncate max-w-[280px]">{r.title || '(无标题)'}</TableCell>
                  <TableCell><Badge variant="secondary">{r.source_type}</Badge></TableCell>
                  <TableCell>
                    <Badge variant={STATUS_VARIANT[r.status] ?? 'outline'}>{r.status}</Badge>
                  </TableCell>
                  <TableCell className="text-xs text-muted-foreground">
                    {r.knowledge_source_id ? `#${r.knowledge_source_id}` : '—'}
                  </TableCell>
                  <TableCell className="text-xs text-muted-foreground">
                    {r.updated_at ? new Date(r.updated_at).toLocaleString() : '—'}
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      <WikiImportDialog open={importOpen} onOpenChange={setImportOpen} onImported={() => load()} />
    </div>
  )
}
