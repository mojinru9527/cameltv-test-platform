import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Card, CardAction, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/ui'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { fetchTaxonomy } from '@/api/testcase'
import type { TaxonomyDomainNode, TaxonomySurfaceNode } from '@/api/testcase'
import { AsyncState } from '@/components/state'
import useApi from '@/hooks/useApi'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import { RotateCcw, Download, Maximize2, Minimize2 } from '@/lib/icons'
import { buildTaxonomyMindmapMarkdown } from './caseTaxonomy'

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
  const [caseType, setCaseType] = useState('manual')
  const [surface, setSurface] = useState('')
  const [domain, setDomain] = useState('')
  const [fullscreen, setFullscreen] = useState(false)
  const [renderError, setRenderError] = useState<string | null>(null)

  // Data fetching（Batch 150 / C147-5：服务端 taxonomy 聚合，替代 page_size=10000 全量拉取）
  const { data: rawData, isLoading, isError, error, refetch } = useApi<TaxonomySurfaceNode[]>(
    (signal) => fetchTaxonomy({ case_type: caseType }, signal),
    [caseType],
  )

  const taxonomy = useMemo(() => rawData || [], [rawData])
  const availableSurfaces = useMemo(() => taxonomy.map((n) => n.surface), [taxonomy])
  const surfaceNode = useMemo(
    () => taxonomy.find((n) => n.surface === surface),
    [taxonomy, surface],
  )
  const domains = useMemo<TaxonomyDomainNode[]>(() => surfaceNode?.domains || [], [surfaceNode])
  const domainNode = useMemo(
    () => domains.find((d) => d.domain === domain),
    [domains, domain],
  )
  const totalCount = useMemo(() => {
    if (domainNode) return domainNode.count
    if (surfaceNode) return surfaceNode.count
    return taxonomy.reduce((sum, n) => sum + (n.count || 0), 0)
  }, [domainNode, surfaceNode, taxonomy])
  const markdown = useMemo(
    () => buildTaxonomyMindmapMarkdown(taxonomy, surface || undefined, domain || undefined),
    [taxonomy, surface, domain],
  )

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

      await new Promise<void>((resolve) => requestAnimationFrame(() => resolve()))

      if (!isCurrentRender() || mmRef.current !== markmap) {
        if (mmRef.current === markmap) {
          mmRef.current = null
          markmap.svg?.interrupt?.()
          markmap.destroy()
        }
        return
      }

      const viewport = svg.getBoundingClientRect()
      const canFit = [viewport.width, viewport.height]
        .every((value) => Number.isFinite(value) && value > 0)

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

  useEffect(() => {
    if (!fullscreen) return
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setFullscreen(false)
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [fullscreen])

  return (
    <div className="space-y-4 p-4 sm:p-6">
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="text-2xl font-bold">脑图视图</h1>

        <Select value={caseType} onValueChange={(value) => {
          setCaseType(value)
          setSurface('')
          setDomain('')
        }}>
          <SelectTrigger className="w-[150px]" size="sm" aria-label="按用例类型筛选">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="manual">功能用例</SelectItem>
            <SelectItem value="api">接口用例</SelectItem>
            <SelectItem value="ui">UI 自动化</SelectItem>
            <SelectItem value="all">全部类型</SelectItem>
          </SelectContent>
        </Select>

        <Select value={surface || undefined} onValueChange={(value) => { setSurface(value || ''); setDomain('') }}>
          <SelectTrigger className="w-[150px]" size="sm" aria-label="按产品界面筛选">
            <SelectValue placeholder="全部界面" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="">全部界面</SelectItem>
            {availableSurfaces.map((item) => (
              <SelectItem key={item} value={item}>{item}</SelectItem>
            ))}
          </SelectContent>
        </Select>

        {/* Domain filter — dynamic from API */}
        <Select value={domain || undefined} onValueChange={(v) => setDomain(v || '')}>
          <SelectTrigger className="w-[160px]" size="sm" aria-label="按用例域筛选">
            <SelectValue placeholder="按域筛选" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="">全部</SelectItem>
            {domains.map((item) => (
              <SelectItem key={item.domain} value={item.domain}>
                {item.domain} ({item.count})
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Button size="sm" variant="secondary" onClick={refetch} disabled={isLoading}>
          <RotateCcw className="size-3.5" data-icon="inline-start" />
          {isLoading ? '加载中...' : '刷新'}
        </Button>

        <div className="flex-1" />

        {!fullscreen && (
          <Button
            size="sm"
            variant="ghost"
            onClick={() => setFullscreen(true)}
            aria-label="全屏"
            title="全屏"
          >
            <Maximize2 className="size-4" />
          </Button>
        )}
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
            用例脑图（产品界面 → 业务域 → 子模块 → 用例）
            {rawData && <span className="ml-2 font-normal text-muted-foreground">({totalCount} 条)</span>}
          </CardTitle>
          {fullscreen && (
            <CardAction>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => setFullscreen(false)}
                aria-label="退出全屏"
                title="退出全屏"
              >
                <Minimize2 className="size-4" />
              </Button>
            </CardAction>
          )}
        </CardHeader>
        <CardContent className="pt-4">
          <AsyncState
            isLoading={isLoading}
            isError={isError}
            error={error}
            data={{ items: taxonomy }}
            onRetry={refetch}
            emptyTitle="暂无测试用例"
            emptyDescription="请先创建测试用例，系统将自动生成脑图"
          >
            <div
              ref={containerRef}
              tabIndex={0}
              role="region"
              aria-label="用例脑图，支持 Ctrl+滚轮 缩放与拖拽平移"
              className="mindmap-canvas min-h-[55vh] overflow-auto rounded-md outline-none focus-visible:ring-2 focus-visible:ring-ring"
              style={{ width: '100%' }}
            />
            <p className="mt-2 text-xs text-muted-foreground">
              键盘：Tab 聚焦脑图后可滚动查看；Ctrl+滚轮 缩放，拖拽平移，Esc 退出全屏。
            </p>
          </AsyncState>
        </CardContent>
      </Card>
    </div>
  )
}
