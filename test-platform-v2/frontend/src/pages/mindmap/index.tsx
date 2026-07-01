import { useEffect, useRef, useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { fetchTestCases } from '@/api/testcase'
import { AsyncState } from '@/components/state'
import useApi from '@/hooks/useApi'
import { RotateCcw, Download } from '@/lib/icons'

// Use markmap to render mindmap from markdown
// The library is loaded dynamically from CDN

export default function MindmapPage() {
  const containerRef = useRef<HTMLDivElement>(null)
  const [domain, setDomain] = useState('')
  const [markmapReady, setMarkmapReady] = useState(false)

  // Load markmap library on mount (CDN only)
  useEffect(() => {
    const script = document.createElement('script')
    script.src = 'https://cdn.jsdelivr.net/npm/markmap-autoloader@0.17'
    script.onload = () => {
      setMarkmapReady(true)
    }
    document.head.appendChild(script)
  }, [])

  // Data fetching with useApi
  const { data: rawData, isLoading, isError, error, refetch } = useApi<any>(
    () => {
      const params: any = { page_size: 1000 }
      if (domain) params.domain = domain
      return fetchTestCases(params)
    },
    [domain],
  )

  // Build markdown from cases and render mindmap when data + CDN are ready
  useEffect(() => {
    if (!markmapReady || !rawData || !containerRef.current) return

    const cases = (rawData as any).items || []

    // Build markdown mind map:
    // # 测试用例
    // ## 用户端
    // ### 登录
    // #### [P0] 正常登录
    //     前置条件: ..., 步骤: ..., 预期: ...
    const tree: Record<string, Record<string, any[]>> = {}
    for (const c of cases) {
      const d = c.domain || '未分类'
      const m = c.module || '通用'
      tree[d] = tree[d] || {}
      tree[d][m] = tree[d][m] || []
      tree[d][m].push(c)
    }

    let md = '# 测试用例\n\n'
    for (const [dom, modules] of Object.entries(tree)) {
      md += `## ${dom}\n`
      for (const [mod, casesInMod] of Object.entries(modules)) {
        md += `### ${mod}\n`
        for (const c of casesInMod) {
          md += `#### [${c.priority}] ${c.title}\n`
          if (c.preconditions) md += `- 前置: ${c.preconditions}\n`
          if (c.expected_result) md += `- 预期: ${c.expected_result}\n`
        }
      }
    }

    // Render with markmap
    const Markmap = (window as any).__Markmap
    const transformer = (window as any).__Transformer
    if (Markmap && transformer) {
      const { root } = transformer.transform(md)
      containerRef.current.innerHTML = ''
      Markmap.create(containerRef.current, undefined, root)
    } else {
      // Fallback: render as plain markdown in a <pre>.
      // Use textContent (not innerHTML) so user-controlled case fields
      // (title / preconditions / expected_result) cannot inject markup — XSS-safe.
      containerRef.current.innerHTML = ''
      const pre = document.createElement('pre')
      pre.style.whiteSpace = 'pre-wrap'
      pre.style.fontSize = '13px'
      pre.textContent = md
      containerRef.current.appendChild(pre)
    }
  }, [rawData, markmapReady, domain])

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center gap-3">
        <h1 className="text-2xl font-bold">脑图视图</h1>
        <Select value={domain || undefined} onValueChange={(v) => setDomain(v || '')}>
          <SelectTrigger className="w-[160px]" size="sm">
            <SelectValue placeholder="按域筛选" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="">全部</SelectItem>
            {['用户端', '运营后台', '接口测试'].map((d) => (
              <SelectItem key={d} value={d}>{d}</SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Button size="sm" variant="outline" onClick={refetch} disabled={isLoading}>
          <RotateCcw className="size-3.5" data-icon="inline-start" />
          {isLoading ? '加载中...' : '刷新'}
        </Button>
        <Button size="sm" variant="outline" onClick={() => {
          const a = document.createElement('a')
          a.href = '/api/v1/test-cases/export/xmind'
          a.download = 'test-cases.xmind'
          a.click()
        }}>
          <Download className="size-3.5" data-icon="inline-start" />
          导出 Xmind
        </Button>
      </div>

      <Card>
        <CardHeader className="border-b pb-2">
          <CardTitle className="text-sm">用例脑图（域 → 模块 → 用例）</CardTitle>
        </CardHeader>
        <CardContent className="pt-4">
          <AsyncState
            isLoading={isLoading}
            isError={isError}
            error={error}
            data={rawData}
            onRetry={refetch}
            emptyTitle="暂无测试用例"
            emptyDescription="请先创建测试用例，系统将自动生成脑图"
          >
            <div
              ref={containerRef}
              className="min-h-[60vh]"
              style={{ width: '100%' }}
            />
          </AsyncState>
        </CardContent>
      </Card>
    </div>
  )
}
