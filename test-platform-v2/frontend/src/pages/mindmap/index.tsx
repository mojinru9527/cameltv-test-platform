import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/ui'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { fetchTestCases } from '@/api/testcase'
import { fetchDomains } from '@/api/testcase'
import { AsyncState } from '@/components/state'
import useApi from '@/hooks/useApi'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import { RotateCcw, Download, Maximize2, Minimize2 } from '@/lib/icons'
import { toast } from 'sonner'

/**
 * MindmapView — interactive test case mindmap.
 *
 * Uses markmap-lib + markmap-view (npm packages) to render test cases
 * as an interactive mindmap (domain → module → test case hierarchy).
 *
 * Install: npm install markmap-lib markmap-view
 */

export default function MindmapPage() {
  useDocumentTitle('思维导图')
  const containerRef = useRef<HTMLDivElement>(null)
  const mmRef = useRef<any>(null)
  const renderVersionRef = useRef(0)
  const [domain, setDomain] = useState('')
  const [domains, setDomains] = useState<any[]>([])
  const [fullscreen, setFullscreen] = useState(false)
  const [renderError, setRenderError] = useState<string | null>(null)

  // Load domains dynamically (not hardcoded)
  useEffect(() => {
    const controller = new AbortController()
    fetchDomains(controller.signal)
      .then((d: any) => setDomains(d || []))
      .catch((fetchError: unknown) => {
        if (controller.signal.aborted) return
        toast.error(fetchError instanceof Error ? fetchError.message : '领域列表加载失败')
      })
    return () => controller.abort()
  }, [])

  // Data fetching
  const { data: rawData, isLoading, isError, error, refetch } = useApi<any>(
    (signal) => {
      const params: any = { page_size: 10000 }
      if (domain) params.domain = domain
      return fetchTestCases(params, signal)
    },
    [domain],
  )

  // Build markdown from cases
  const markdown = useMemo(() => {
    const cases = (rawData as any)?.items || []
    if (!cases.length) return '# 测试用例\n\n暂无用例数据'

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
    return md
  }, [rawData])

  const destroyMindmap = useCallback(() => {
    const markmap = mmRef.current
    mmRef.current = null
    markmap?.svg?.interrupt?.()
    markmap?.destroy?.()
  }, [])

  // Render mindmap — try npm packages first, fall back to CDN
  const renderMindmap = useCallback(async () => {
    if (!containerRef.current || !markdown) return

    const renderVersion = ++renderVersionRef.current
    const container = containerRef.current
    const isCurrentRender = () =>
      renderVersionRef.current === renderVersion
      && containerRef.current === container
      && container.isConnected

    destroyMindmap()

    const renderCDN = () => {
      const M = (window as any).__Markmap
      const T = (window as any).__Transformer
      if (M && T) {
        const { root } = T.transform(markdown)
        container.innerHTML = ''
        mmRef.current = M.create(container, undefined, root)
        setRenderError(null)
        return true
      }
      return false
    }

    // Try CDN first (always available since we load the script)
    if (renderCDN()) return

    // Try npm packages
    try {
      // @ts-ignore — markmap packages are optional dependencies
      const markmapLib = await import('markmap-lib')
      // @ts-ignore
      const markmapView = await import('markmap-view')

      if (!isCurrentRender()) return

      const transformer = new markmapLib.Transformer()
      const { root } = transformer.transform(markdown)
      container.innerHTML = ''
      const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg')
      svg.setAttribute('width', '100%')
      svg.setAttribute('height', fullscreen ? '85vh' : '55vh')
      container.appendChild(svg)
      const markmap = markmapView.Markmap.create(
        svg,
        { autoFit: false, duration: 300, maxWidth: 320, initialExpandLevel: 2 },
      )
      mmRef.current = markmap
      await markmap.setData(root)

      if (!isCurrentRender() || mmRef.current !== markmap) {
        if (mmRef.current === markmap) {
          mmRef.current = null
          markmap.svg?.interrupt?.()
          markmap.destroy()
        }
        return
      }

      const viewport = svg.getBoundingClientRect()
      const rect = markmap.state?.rect
      const contentWidth = rect ? rect.x2 - rect.x1 : 0
      const contentHeight = rect ? rect.y2 - rect.y1 : 0
      const canFit = [
        viewport.width,
        viewport.height,
        contentWidth,
        contentHeight,
      ].every((value) => Number.isFinite(value) && value > 0)

      if (canFit) {
        await markmap.fit()
      }
      setRenderError(null)
    } catch {
      if (!isCurrentRender()) return
      // Ultimate fallback: plain text
      destroyMindmap()
      container.innerHTML = ''
      const pre = document.createElement('pre')
      pre.style.whiteSpace = 'pre-wrap'
      pre.style.fontSize = '13px'
      pre.style.padding = '1rem'
      pre.textContent = markdown
      container.appendChild(pre)
      setRenderError('markmap not available — install with: npm install markmap-lib markmap-view')
    }
  }, [destroyMindmap, markdown, fullscreen])

  useEffect(() => {
    let timer: ReturnType<typeof setTimeout> | undefined
    if (!isLoading) {
      // Small delay to ensure DOM is ready
      timer = setTimeout(() => { void renderMindmap() }, 100)
    }

    return () => {
      if (timer) clearTimeout(timer)
      renderVersionRef.current += 1
      destroyMindmap()
    }
  }, [destroyMindmap, isLoading, renderMindmap])

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center gap-3">
        <h1 className="text-2xl font-bold">脑图视图</h1>

        {/* Domain filter — dynamic from API */}
        <Select value={domain || undefined} onValueChange={(v) => setDomain(v || '')}>
          <SelectTrigger className="w-[160px]" size="sm">
            <SelectValue placeholder="按域筛选" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="">全部</SelectItem>
            {domains.map((d: any) => (
              <SelectItem key={d.domain} value={d.domain}>
                {d.domain} ({d.count})
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Button size="sm" variant="secondary" onClick={refetch} disabled={isLoading}>
          <RotateCcw className="size-3.5" data-icon="inline-start" />
          {isLoading ? '加载中...' : '刷新'}
        </Button>

        <div className="flex-1" />

        <Button
          size="sm"
          variant="ghost"
          onClick={() => setFullscreen(!fullscreen)}
          title={fullscreen ? '退出全屏' : '全屏'}
        >
          {fullscreen ? <Minimize2 className="size-4" /> : <Maximize2 className="size-4" />}
        </Button>
      </div>

      {renderError && (
        <div className="rounded-md bg-status-warning-muted border border-status-warning-border p-2 text-xs text-status-warning">
          npm packages not available, using fallback renderer.
          Run: <code className="font-mono bg-status-warning-muted px-1">npm install markmap-lib markmap-view</code>
        </div>
      )}

      <Card className={fullscreen ? 'fixed inset-4 z-50' : ''}>
        <CardHeader className="border-b pb-2">
          <CardTitle className="text-sm">
            用例脑图（域 → 模块 → 用例）
            {rawData && <span className="ml-2 text-muted-foreground font-normal">({(rawData as any)?.items?.length || 0} 条)</span>}
          </CardTitle>
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
              className="min-h-[55vh] overflow-auto"
              style={{ width: '100%' }}
            />
          </AsyncState>
        </CardContent>
      </Card>
    </div>
  )
}
