import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { toast } from 'sonner'
import { Plus, Search, FileUp, RefreshCw, FlaskConical, Zap, ChevronLeft, ChevronRight, ChevronDown } from '@/lib/icons'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible'
import { Sheet, SheetContent } from '@/components/ui/sheet'
import { fetchApiServices, fetchApiEndpoints, generateApiCases } from '@/api/apitest'
import EndpointDetailPanel from './EndpointDetailPanel'
import type { ApiService, ApiEndpoint } from '@/types'

const METHOD_COLORS: Record<string, string> = {
  GET: 'bg-blue-100 text-blue-700', POST: 'bg-green-100 text-green-700',
  PUT: 'bg-orange-100 text-orange-700', PATCH: 'bg-purple-100 text-purple-700',
  DELETE: 'bg-red-100 text-red-700',
}

interface Props {
  onDebugEndpoint?: (ep: ApiEndpoint) => void
  onOpenImport: () => void
  refreshKey: number
}

export default function AssetTab({ onDebugEndpoint, onOpenImport, refreshKey }: Props) {
  const [services, setServices] = useState<ApiService[]>([])
  const [selectedService, setSelectedService] = useState<number | undefined>()
  const [endpoints, setEndpoints] = useState<ApiEndpoint[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [keyword, setKeyword] = useState('')
  const [methodFilter, setMethodFilter] = useState<string>('')
  const [generating, setGenerating] = useState<Set<number>>(new Set())
  const [selectedEndpoint, setSelectedEndpoint] = useState<ApiEndpoint | null>(null)

  // Tab state
  const [activeTab, setActiveTab] = useState('_all')

  // Tab scroll state
  const tabsScrollRef = useRef<HTMLDivElement>(null)
  const [canScrollLeft, setCanScrollLeft] = useState(false)
  const [canScrollRight, setCanScrollRight] = useState(false)

  const loadServices = useCallback(async () => {
    try { setServices(await fetchApiServices()) } catch { setServices([]) }
  }, [])

  const loadEndpoints = useCallback(async () => {
    try {
      const result = await fetchApiEndpoints({
        service_id: selectedService,
        method: methodFilter || undefined,
        keyword: keyword || undefined,
        page, page_size: 20,
      })
      setEndpoints(result.items)
      setTotal(result.total)
    } catch { setEndpoints([]) }
  }, [selectedService, methodFilter, keyword, page, refreshKey])

  useEffect(() => { loadServices() }, [loadServices])
  useEffect(() => { loadEndpoints() }, [loadEndpoints])

  // Module grouping
  const moduleGroups = useMemo(() => {
    return endpoints.reduce<Record<string, ApiEndpoint[]>>((acc, ep) => {
      const key = ep.module || '默认模块'
      if (!acc[key]) acc[key] = []
      acc[key].push(ep)
      return acc
    }, {})
  }, [endpoints])

  // Tab scroll helpers
  const checkScroll = useCallback(() => {
    const el = tabsScrollRef.current
    if (!el) return
    setCanScrollLeft(el.scrollLeft > 1)
    setCanScrollRight(el.scrollLeft + el.clientWidth < el.scrollWidth - 1)
  }, [])

  useEffect(() => {
    // Initial check after render
    checkScroll()
    const el = tabsScrollRef.current
    if (!el) return
    const observer = new ResizeObserver(checkScroll)
    observer.observe(el)
    el.addEventListener('scroll', checkScroll)
    return () => {
      observer.disconnect()
      el.removeEventListener('scroll', checkScroll)
    }
  }, [services, checkScroll])

  const scrollTabs = (direction: 'left' | 'right') => {
    const el = tabsScrollRef.current
    if (!el) return
    el.scrollBy({ left: direction === 'left' ? -200 : 200, behavior: 'smooth' })
  }

  const handleTabChange = (value: string) => {
    setActiveTab(value)
    setSelectedService(value === '_all' ? undefined : Number(value))
    setPage(1)
  }

  const handleGenerate = async (ep: ApiEndpoint) => {
    setGenerating(prev => new Set(prev).add(ep.id))
    try {
      const result = await generateApiCases({
        endpoint_id: ep.id,
        templates: ['basic', 'boundary', 'invalid', 'idempotency'],
        import_to_case_library: true,
        service_name: services.find(s => s.id === ep.service_id)?.name || '',
        module: ep.module,
      })
      toast.success(`为 "${ep.summary || ep.path}" 生成了 ${result.total} 条用例`)
    } catch (e: any) {
      toast.error(e?.message || '生成失败')
    } finally {
      setGenerating(prev => { const s = new Set(prev); s.delete(ep.id); return s })
    }
  }

  return (
    <div className="space-y-4">
      {/* Toolbar */}
      <div className="flex items-center gap-3 flex-wrap">
        <Select value={methodFilter || '_all'} onValueChange={v => { setMethodFilter(v === '_all' ? '' : v); setPage(1) }}>
          <SelectTrigger className="w-[120px]"><SelectValue placeholder="全部方法" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="_all">全部方法</SelectItem>
            {['GET','POST','PUT','PATCH','DELETE'].map(m => <SelectItem key={m} value={m}>{m}</SelectItem>)}
          </SelectContent>
        </Select>
        <div className="flex items-center gap-1 flex-1 min-w-[200px]">
          <Search className="size-4 text-muted-foreground shrink-0" />
          <Input placeholder="搜索路径/描述..." value={keyword} onChange={e => { setKeyword(e.target.value); setPage(1) }} className="border-0 shadow-none" />
        </div>
        <Button variant="outline" onClick={loadEndpoints} data-icon="inline-start"><RefreshCw className="size-4" /></Button>
        <Button onClick={onOpenImport} data-icon="inline-start"><FileUp className="size-4" /> 导入接口</Button>
      </div>

      {/* Service Tabs with scroll buttons */}
      <Tabs value={activeTab} onValueChange={handleTabChange}>
        <div className="relative flex items-center">
          {canScrollLeft && (
            <Button
              variant="ghost"
              size="icon-sm"
              className="shrink-0"
              onClick={() => scrollTabs('left')}
            >
              <ChevronLeft className="size-4" />
            </Button>
          )}
          <div
            ref={tabsScrollRef}
            className="overflow-x-auto scrollbar-none flex-1"
            onScroll={checkScroll}
          >
            <TabsList className="h-auto max-w-full justify-start w-max">
              <TabsTrigger value="_all">全部服务 ({total})</TabsTrigger>
              {services.map(s => (
                <TabsTrigger key={s.id} value={s.id.toString()}>
                  {s.display_name || s.name}
                </TabsTrigger>
              ))}
            </TabsList>
          </div>
          {canScrollRight && (
            <Button
              variant="ghost"
              size="icon-sm"
              className="shrink-0"
              onClick={() => scrollTabs('right')}
            >
              <ChevronRight className="size-4" />
            </Button>
          )}
        </div>

        <TabsContent value={activeTab} className="mt-3">
          {/* Stats */}
          <p className="text-sm text-muted-foreground">{total} 个接口资产</p>

          {/* Module Collapsible groups */}
          <div className="mt-2 space-y-2">
            {Object.keys(moduleGroups).length === 0 ? (
              <div className="border rounded-lg py-12 text-center text-muted-foreground">
                <p className="text-sm">暂无接口资产</p>
                <p className="text-xs mt-1">点击「导入接口」从 Swagger/OpenAPI 导入</p>
              </div>
            ) : (
              Object.entries(moduleGroups).map(([moduleName, eps]) => (
                <Collapsible key={moduleName} defaultOpen={false}>
                  <CollapsibleTrigger className="flex items-center gap-2 w-full px-4 py-2 text-sm font-medium hover:bg-muted/50 rounded-lg transition-colors group">
                    <ChevronDown className="size-4 shrink-0 transition-transform duration-200 group-data-[state=open]:rotate-180" />
                    <span>{moduleName}</span>
                    <Badge variant="secondary" className="ml-auto text-xs">{eps.length}</Badge>
                  </CollapsibleTrigger>
                  <CollapsibleContent className="border rounded-lg divide-y mt-1">
                    {eps.map(ep => (
                      <div
                        key={ep.id}
                        className="flex items-center gap-3 px-4 py-3 hover:bg-muted/50 transition-colors cursor-pointer"
                        onClick={() => setSelectedEndpoint(ep)}
                      >
                        <Badge className={METHOD_COLORS[ep.method] || ''}>{ep.method}</Badge>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <code className="text-sm font-medium truncate">{ep.path.replace(/\//g, '-')}</code>
                            {ep.deprecated && <Badge variant="outline" className="text-[10px] text-yellow-600">已废弃</Badge>}
                          </div>
                          <p className="text-xs text-muted-foreground truncate">
                            {ep.summary && `${ep.summary} · `}{ep.module}
                            {ep.remark && <span className="ml-2 text-muted-foreground/60">📝 {ep.remark}</span>}
                          </p>
                        </div>
                        <div className="flex items-center gap-1 shrink-0">
                          {onDebugEndpoint && (
                            <Button
                              size="icon-sm"
                              variant="ghost"
                              title="调试"
                              onClick={(e) => { e.stopPropagation(); onDebugEndpoint(ep) }}
                            >
                              <FlaskConical className="size-4" />
                            </Button>
                          )}
                          <Button
                            size="icon-sm"
                            variant="ghost"
                            title="生成用例"
                            onClick={(e) => { e.stopPropagation(); handleGenerate(ep) }}
                            disabled={generating.has(ep.id)}
                          >
                            <Zap className={`size-4 ${generating.has(ep.id) ? 'animate-pulse' : ''}`} />
                          </Button>
                        </div>
                      </div>
                    ))}
                  </CollapsibleContent>
                </Collapsible>
              ))
            )}
          </div>

          {/* Pagination */}
          {total > 20 && (
            <div className="flex items-center justify-between mt-4">
              <span className="text-xs text-muted-foreground">第 {page}/{Math.ceil(total / 20)} 页</span>
              <div className="flex gap-1">
                <Button size="sm" variant="outline" disabled={page <= 1} onClick={() => setPage(p => p - 1)}>上一页</Button>
                <Button size="sm" variant="outline" disabled={page * 20 >= total} onClick={() => setPage(p => p + 1)}>下一页</Button>
              </div>
            </div>
          )}
        </TabsContent>
      </Tabs>

      {/* Endpoint detail Sheet */}
      <Sheet open={!!selectedEndpoint} onOpenChange={(open) => { if (!open) setSelectedEndpoint(null) }}>
        <SheetContent side="right" className="w-full sm:max-w-xl p-0">
          {selectedEndpoint && (
            <EndpointDetailPanel endpoint={selectedEndpoint} />
          )}
        </SheetContent>
      </Sheet>
    </div>
  )
}
