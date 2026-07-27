import { useCallback, useEffect, useState } from 'react'
import { BrainCircuit, Loader2 } from '@/lib/icons'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { searchKnowledge } from '@/api/knowledge'
import type { ApiEndpoint, KnowledgeSearchResult } from '@/types'

const METHOD_COLORS: Record<string, string> = {
  GET: 'bg-blue-100 text-blue-700', POST: 'bg-green-100 text-green-700',
  PUT: 'bg-orange-100 text-orange-700', PATCH: 'bg-purple-100 text-purple-700',
  DELETE: 'bg-red-100 text-red-700',
}

const CHUNK_LABEL: Record<string, string> = {
  requirement_rule: '需求',
  api_schema: '接口',
  test_case: '用例',
  defect_case: '缺陷',
  execution_result: '执行',
  field_rule: '字段',
}

interface Props {
  endpoint: ApiEndpoint
}

export default function EndpointDetailPanel({ endpoint }: Props) {
  const [results, setResults] = useState<KnowledgeSearchResult[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const query = [endpoint.method, endpoint.path, endpoint.summary || '']
    .filter(Boolean)
    .join(' ')

  const doSearch = useCallback(() => {
    setLoading(true)
    setError(null)
    searchKnowledge({ query, mode: 'hybrid', top_k: 10 })
      .then((res) => setResults(res || []))
      .catch((e) => {
        setResults([])
        const status = e?.response?.status || e?.status
        if (status === 503) {
          setError('RAG 检索未启用')
        } else if (status === 403) {
          setError('暂无权限查看知识库')
        } else {
          setError('检索暂不可用')
        }
      })
      .finally(() => setLoading(false))
  }, [query])

  useEffect(() => {
    doSearch()
  }, [doSearch])

  return (
    <div className="flex flex-col h-full max-h-[100dvh]">
      {/* Header — sticky */}
      <div className="p-4 border-b bg-muted/10 shrink-0">
        <div className="flex items-center gap-2 mb-1">
          <Badge className={METHOD_COLORS[endpoint.method] || ''}>{endpoint.method}</Badge>
          {endpoint.deprecated && (
            <Badge variant="outline" className="text-[10px] text-yellow-600">已废弃</Badge>
          )}
        </div>
        <code className="text-sm font-medium break-all block mt-1">{endpoint.path}</code>
        {endpoint.summary && (
          <p className="text-sm text-foreground mt-1 font-medium">{endpoint.summary}</p>
        )}
        <div className="flex items-center gap-2 mt-2 flex-wrap">
          {endpoint.module && (
            <Badge variant="secondary" className="text-[10px]">{endpoint.module}</Badge>
          )}
          {endpoint.auth_required && (
            <Badge variant="outline" className="text-[10px]">需认证</Badge>
          )}
          {endpoint.source && (
            <span className="text-[10px] text-muted-foreground">
              来源：{endpoint.source}
            </span>
          )}
        </div>
        {endpoint.description && (
          <p className="text-xs text-muted-foreground mt-2 leading-relaxed whitespace-pre-wrap">
            {endpoint.description}
          </p>
        )}
      </div>

      {/* Knowledge section — scrollable */}
      <div className="flex-1 overflow-y-auto p-4">
        <h3 className="flex items-center gap-1.5 text-sm font-medium mb-3">
          <BrainCircuit className="size-4" />
          相关知识
        </h3>

        {loading ? (
          <div className="space-y-2">
            {[1, 2, 3].map((i) => (
              <Card key={i}>
                <CardContent className="p-3 space-y-2">
                  <div className="flex items-center gap-2">
                    <Skeleton className="h-5 w-12" />
                    <Skeleton className="h-4 flex-1" />
                  </div>
                  <Skeleton className="h-3 w-full" />
                  <Skeleton className="h-3 w-3/4" />
                </CardContent>
              </Card>
            ))}
          </div>
        ) : error ? (
          <div className="py-8 text-center text-sm text-muted-foreground">
            <p>{error}</p>
          </div>
        ) : results.length === 0 ? (
          <div className="py-8 text-center text-sm text-muted-foreground">
            <p>暂无相关知识</p>
            <p className="text-xs mt-1">导入接口或生成用例后，相关知识切片将自动关联</p>
          </div>
        ) : (
          <div className="space-y-2">
            {results.map((r) => (
              <Card key={r.chunk_id}>
                <CardContent className="p-3 space-y-1">
                  <div className="flex items-center gap-2">
                    <Badge variant="secondary" className="shrink-0">
                      {CHUNK_LABEL[r.chunk_type] ?? r.chunk_type}
                    </Badge>
                    <span className="text-sm font-medium truncate">{r.title || '(无标题)'}</span>
                    <span className="ml-auto text-xs text-muted-foreground shrink-0">
                      {r.score.toFixed(4)}
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
    </div>
  )
}
