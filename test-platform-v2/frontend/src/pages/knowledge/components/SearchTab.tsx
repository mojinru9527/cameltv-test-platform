import { useState } from 'react'
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
import { searchKnowledge, reembedKnowledge } from '@/api/knowledge'
import type { KnowledgeSearchResult } from '@/types'
import { useAuthStore } from '@/stores/auth'
import { Search, Loader2, RefreshCw } from '@/lib/icons'

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

export default function SearchTab() {
  const hasPerm = useAuthStore((s) => s.hasPerm)
  const [query, setQuery] = useState('')
  const [mode, setMode] = useState('hybrid')
  const [results, setResults] = useState<KnowledgeSearchResult[]>([])
  const [loading, setLoading] = useState(false)
  const [searched, setSearched] = useState(false)
  const [reembedding, setReembedding] = useState(false)

  const doSearch = () => {
    const q = query.trim()
    if (!q) return
    setLoading(true)
    setSearched(true)
    searchKnowledge({ query: q, mode: mode as 'hybrid' | 'keyword' | 'vector', top_k: 10 })
      .then((res) => setResults(res || []))
      .catch((e) => {
        setResults([])
        toast.error(e?.message || 'RAG 检索未启用或不可用')
      })
      .finally(() => setLoading(false))
  }

  const doReembed = () => {
    setReembedding(true)
    reembedKnowledge()
      .then((r) => toast.success(`回填完成：共 ${r.total} 条，已嵌入 ${r.embedded}，跳过 ${r.skipped}`))
      .catch((e) => toast.error(e?.message || '回填失败（需启用 RAG 且模型就绪）'))
      .finally(() => setReembedding(false))
  }

  return (
    <div className="space-y-4">
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
