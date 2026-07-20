import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { toast } from 'sonner'
import { Search, FileUp, RefreshCw, FlaskConical, Zap, ChevronLeft, ChevronRight, ChevronDown, FolderOpen, ArrowRight } from '@/lib/icons'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
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

  // Service → Module → Path-group → Endpoints (hierarchy)
  // "全部服务" tab: shows Service level → Module → Path-group
  // Single-service tab: shows Module → Path-group directly
  const hierarchy = useMemo(() => {
    // Record<serviceName, Record<moduleName, Record<pathGroup, ApiEndpoint[]>>>
    const result: Record<string, Record<string, Record<string, ApiEndpoint[]>>> = {}
    for (const ep of endpoints) {
      const svcName = services.find(s => s.id === ep.service_id)?.display_name
        || services.find(s => s.id === ep.service_id)?.name
        || '未分类'
      const mod = ep.module || '默认模块'
      const pathParts = (ep.path || '/').split('/').filter(Boolean)
      const pathGroup = pathParts.length > 0 ? `/${pathParts[0]}` : '/'
      if (!result[svcName]) result[svcName] = {}
      if (!result[svcName][mod]) result[svcName][mod] = {}
      if (!result[svcName][mod][pathGroup]) result[svcName][mod][pathGroup] = []
      result[svcName][mod][pathGroup].push(ep)
    }
    return result
  }, [endpoints, services])

  // Tab scroll helpers
  const checkScroll = useCallback(() => {
    const el = tabsScrollRef.current
    if (!el) return
    setCanScrollLeft(el.scrollLeft > 1)
    setCanScrollRight(el.scrollLeft + el.clientWidth < el.scrollWidth - 1)
  }, [])

  useEffect(() => {
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
        templates: ['basic', 'boundary', 'invalid', 'idempotency', 'security', 'extreme'],
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

  // Render endpoint rows within a pathGroup
  const renderEndpointRows = (eps: ApiEndpoint[]) => eps.map(ep => (
    <div
      key={ep.id}
      className="flex items-center gap-3 px-4 py-3 hover:bg-muted/50 transition-colors cursor-pointer pl-10"
      onClick={() => setSelectedEndpoint(ep)}
    >
      <Badge className={METHOD_COLORS[ep.method] || ''}>{ep.method}</Badge>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <code className="text-sm font-medium truncate">{ep.path}</code>
          {ep.deprecated && <Badge variant="outline" className="text-[10px] text-yellow-600">已废弃</Badge>}
        </div>
        <p className="text-xs text-muted-foreground truncate">
          {ep.summary || '-'}
        </p>
      </div>
      <span className="text-xs text-muted-foreground truncate max-w-[120px]" title={ep.remark || ''}>
        {ep.remark || '-'}
      </span>
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
  ))

  // Render modules within a service (or standalone for single-service tab)
  const renderModules = (modules: Record<string, Record<string, ApiEndpoint[]>>) =>
    Object.entries(modules).map(([moduleName, pathGroups]) => {
      const totalInModule = Object.values(pathGroups).reduce((sum, eps) => sum + eps.length, 0)
      return (
        <Collapsible key={moduleName} defaultOpen={false}>
          <CollapsibleTrigger className="flex items-center gap-2 w-full px-4 py-2 text-sm font-medium hover:bg-muted/50 rounded-lg transition-colors group">
            <ChevronDown className="size-4 shrink-0 transition-transform duration-200 group-data-[state=open]:rotate-180" />
            <FolderOpen className="size-4 text-muted-foreground" />
            <span>{moduleName}</span>
            <Badge variant="secondary" className="ml-auto text-xs">
              {totalInModule}
            </Badge>
          </CollapsibleTrigger>
          <CollapsibleContent className="border rounded-lg divide-y mt-1">
            {Object.entries(pathGroups).map(([pathGroup, eps]) => (
              <div key={pathGroup}>
                {/* Path group header — inline label */}
                <div className="flex items-center gap-2 px-4 py-1.5 bg-muted/30 text-xs text-muted-foreground font-mono">
                  <ArrowRight className="size-3" />
                  <span>{pathGroup}</span>
                  <span className="ml-auto">{eps.length} 个接口</span>
                </div>
                {renderEndpointRows(eps)}
              </div>
            ))}
          </CollapsibleContent>
        </Collapsible>
      )
    })

  // Render content for the selected tab
  const renderTabContent = () => {
    const serviceNames = Object.keys(hierarchy)
    if (serviceNames.length === 0) {
      return (
        <div className="border rounded-lg py-12 text-center text-muted-foreground">
          <p className="text-sm">暂无接口资产</p>
          <p className="text-xs mt-1">点击「导入接口」从 Swagger/OpenAPI 导入</p>
        </div>
      )
    }

    // Single-service tab: render modules directly
    if (activeTab !== '_all') {
      // Flatten all service entries into modules (there should be only one service)
      const allModules: Record<string, Record<string, ApiEndpoint[]>> = {}
      for (const svcModules of Object.values(hierarchy)) {
        Object.assign(allModules, svcModules)
      }
      return <div className="space-y-2">{renderModules(allModules)}</div>
    }

    // "全部服务" tab: render service → module hierarchy
    return (
      <div className="space-y-2">
        {serviceNames.map(svcName => {
          const modules = hierarchy[svcName]
          const totalInSvc = Object.values(modules).reduce(
            (sum, pathGroups) => sum + Object.values(pathGroups).reduce((s, eps) => s + eps.length, 0), 0
          )
          return (
            <Collapsible key={svcName} defaultOpen={false}>
              <CollapsibleTrigger className="flex items-center gap-2 w-full px-4 py-3 text-sm font-semibold hover:bg-muted/50 rounded-lg transition-colors group border bg-muted/20">
                <ChevronDown className="size-4 shrink-0 transition-transform duration-200 group-data-[state=open]:rotate-180" />
                <FolderOpen className="size-4 text-primary" />
                <span>{svcName}</span>
                <Badge variant="secondary" className="ml-auto text-xs">
                  {totalInSvc} 个接口
                </Badge>
              </CollapsibleTrigger>
              <CollapsibleContent className="mt-1 ml-4 space-y-2">
                {renderModules(modules)}
              </CollapsibleContent>
            </Collapsible>
          )
        })}
      </div>
    )
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
          <Input placeholder="搜索服务/模块/路径/描述..." value={keyword} onChange={e => { setKeyword(e.target.value); setPage(1) }} className="border-0 shadow-none" />
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
              aria-label="向左查看更多服务"
            >
              <ChevronLeft className="size-4" />
            </Button>
          )}
          <div
            ref={tabsScrollRef}
            className="overflow-x-auto scrollbar-none flex-1"
            onScroll={checkScroll}
            data-testid="service-tabs-viewport"
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
              aria-label="向右查看更多服务"
            >
              <ChevronRight className="size-4" />
            </Button>
          )}
        </div>

        <TabsContent value={activeTab} className="mt-3">
          {/* Stats */}
          <p className="text-sm text-muted-foreground">{total} 个接口资产</p>

          {/* Hierarchy: Service → Module → Path-group → Endpoints */}
          <div className="mt-2">
            {renderTabContent()}
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
