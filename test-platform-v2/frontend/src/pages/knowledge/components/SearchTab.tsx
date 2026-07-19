import { useState, useEffect } from 'react'
import { toast } from 'sonner'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { searchKnowledge, reembedKnowledge, fetchSearchHealth } from '@/api/knowledge'
import type { KnowledgeSearchResult, SearchHealth } from '@/types'
import { useAuthStore } from '@/stores/auth'
import { Search, Loader2, RefreshCw, AlertTriangle, CheckCircle2, Database, BrainCircuit } from '@/lib/icons'

const MODES = [
  { v: 'hybrid', l: '混合（关键词+向量）' },
  { v: 'keyword', l: '关键词' },
  { v: 'vector', l: '向量语义' },
]

const CHUNK_LABEL: Record<string, string> = {
  requirement_rule: '需求',
  api_schema: '接口',
  test_case: '用例',
  defect_case: '缺陷',
  execution_result: '执行',
  field_rule: '字段',
}

const FALLBACK_LABEL: Record<string, string> = {
  'keyword-only': '仅关键词',
  'hybrid': '混合（关键词+向量）',
}

export default function SearchTab() {
  const hasPerm = useAuthStore((s) => s.hasPerm)
  const [query, setQuery] = useState('')
  const [mode, setMode] = useState('hybrid')
  const [results, setResults] = useState<KnowledgeSearchResult[]>([])
  const [loading, setLoading] = useState(false)
  const [searched, setSearched] = useState(false)
  const [searchError, setSearchError] = useState<string | null>(null)
  const [reembedding, setReembedding] = useState(false)
  const [health, setHealth] = useState<SearchHealth | null>(null)

  useEffect(() => {
    fetchSearchHealth()
      .then(setHealth)
      .catch(() => { /* 静默——健康检查失败不影响主功能 */ })
  }, [])

  const refreshHealth = () => {
    fetchSearchHealth()
      .then(setHealth)
      .catch(() => toast.error('获取搜索健康状态失败'))
  }

  const doSearch = () => {
    const q = query.trim()
    if (!q) return
    setLoading(true)
    setSearched(true)
    setSearchError(null)
    searchKnowledge({ query: q, mode: mode as 'hybrid' | 'keyword' | 'vector', top_k: 10 })
      .then((res) => setResults(res || []))
      .catch((e) => {
        setResults([])
        setSearchError(e?.message || '检索失败')
      })
      .finally(() => setLoading(false))
  }

  const doReembed = () => {
    setReembedding(true)
    reembedKnowledge()
      .then((r) => {
        toast.success(`回填完成：共 ${r.total} 条，已嵌入 ${r.embedded}，跳过 ${r.skipped}`)
        refreshHealth()
      })
      .catch((e) => toast.error(e?.message || '回填失败（需启用 RAG 且模型就绪）'))
      .finally(() => setReembedding(false))
  }

  const ragStatusBadge = () => {
    if (!health) return null
    if (health.rag_enabled && health.vector_search_functional) {
      return <Badge variant="default" className="text-xs gap-1"><CheckCircle2 className="size-3" />RAG 已启用</Badge>
    }
    if (health.rag_enabled) {
      return <Badge variant="secondary" className="text-xs gap-1"><AlertTriangle className="size-3" />RAG 降级</Badge>
    }
    return <Badge variant="outline" className="text-xs gap-1"><Database className="size-3" />仅关键词</Badge>
  }

  const coveragePct = health?.embedding_coverage != null
    ? Math.round(health.embedding_coverage * 100)
    : null

  return (
    <div className="space-y-4">
      {/* RAG 健康状态栏 */}
      {health && (
        <div className="flex flex-wrap items-center gap-3 px-3 py-2 bg-muted/40 rounded-md text-xs">
          {ragStatusBadge()}
          <span className="text-muted-foreground">
            检索模式：<span className="font-medium text-foreground">{FALLBACK_LABEL[health.fallback_mode] ?? health.fallback_mode}</span>
          </span>
          {health.rag_enabled && (
            <>
              <span className="text-muted-foreground">
                模型：<span className="font-medium text-foreground">{health.embedding_model}</span>
              </span>
              <span className="text-muted-foreground">
                切片：<span className="font-medium text-foreground">{health.embedded_chunks}/{health.active_chunks}</span>
              </span>
              {/* 嵌入覆盖率进度条 */}
              {coveragePct != null && (
                <div className="flex items-center gap-1.5">
                  <span className="text-muted-foreground shrink-0">覆盖率：</span>
                  <div className="w-20 h-2 bg-muted rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all ${coveragePct >= 80 ? 'bg-green-500' : coveragePct >= 40 ? 'bg-amber-500' : 'bg-red-500'}`}
                      style={{ width: `${coveragePct}%` }}
                    />
                  </div>
                  <span className="font-medium tabular-nums">{coveragePct}%</span>
                </div>
              )}
              {health.embedding_available && (
                <span className="text-muted-foreground flex items-center gap-1">
                  <BrainCircuit className="size-3" />模型就绪
                </span>
              )}
            </>
          )}
          <button
            type="button"
            className="ml-auto text-muted-foreground hover:text-foreground"
            onClick={refreshHealth}
            title="刷新健康状态"
          >
            <RefreshCw className="size-3" />
          </button>
        </div>
      )}

      <div className="flex items-center gap-2">
        <div className="relative flex-1">
          <Search className="absolute left-2 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
          <Input
            className="pl-8 h-9"
            placeholder="语义检索知识库（如：密码字段参数校验）"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter' && !loading) doSearch() }}
          />
        </div>
        <Select value={mode} onValueChange={setMode}>
          <SelectTrigger className="h-9 text-xs w-[180px]">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {MODES.map((m) => (
              <SelectItem key={m.v} value={m.v}>
                {m.l}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Button size="sm" className="h-9" disabled={loading || !query.trim()} onClick={doSearch}>
          {loading ? <Loader2 className="size-4 animate-spin" /> : '搜索'}
        </Button>
        {hasPerm('knowledge:manage') && (
          <Button
            variant="outline"
            size="sm"
            className="h-9"
            disabled={reembedding}
            onClick={doReembed}
            title="为存量切片补齐向量（幂等）"
          >
            {reembedding ? (
              <Loader2 className="size-4 animate-spin" />
            ) : (
              <RefreshCw className="size-4" />
            )}
            <span className="ml-1">向量回填</span>
          </Button>
        )}
      </div>

      {loading ? (
        <div className="h-24 flex items-center justify-center">
          <Loader2 className="size-5 animate-spin text-muted-foreground" />
        </div>
      ) : searchError ? (
        <div className="h-24 flex flex-col items-center justify-center gap-1">
          <span className="text-sm text-amber-600 font-medium">检索异常</span>
          <span className="text-xs text-muted-foreground">{searchError}</span>
        </div>
      ) : results.length === 0 ? (
        <div className="h-24 flex items-center justify-center text-sm text-muted-foreground">
          {searched ? '暂无相关知识' : '输入关键词后检索需求 / 接口 / 用例 / 缺陷 / 执行等知识切片'}
        </div>
      ) : (
        <div className="space-y-2">
          {results.map((r) => (
            <Card key={r.chunk_id}>
              <CardContent className="p-3 space-y-1">
                <div className="flex items-center gap-2">
                  <Badge variant="secondary">{CHUNK_LABEL[r.chunk_type] ?? r.chunk_type}</Badge>
                  <span className="text-sm font-medium truncate">{r.title || '(无标题)'}</span>
                  <span className="ml-auto text-xs text-muted-foreground shrink-0">
                    相关度 {r.score.toFixed(4)}
                  </span>
                </div>
                <p className="text-xs text-muted-foreground break-words">{r.snippet}</p>
                {r.source_name && (
                  <div className="text-[11px] text-muted-foreground">来源：{r.source_name}</div>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
