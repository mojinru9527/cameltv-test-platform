import { useState, useEffect, useRef, useCallback, useMemo } from 'react'
import { Network } from 'vis-network'
import { DataSet } from 'vis-data'
import { toast } from 'sonner'
import { fetchGraphHierarchy } from '@/api/knowledge'
import { fetchReleaseBundles } from '@/api/releaseBundles'
import type { ProjectSphereView, ProjectSphereNode, ProjectSphereEdge } from '@/types'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group'
import {
  Layers,
  RefreshCw,
  ArrowRight,
  GitGraph,
  List,
} from '@/lib/icons'
import { cn } from '@/lib/utils'
import { useApi } from '@/hooks/useApi'

// ── Node colors by entity type ──
const NODE_COLORS: Record<string, { background: string; border: string }> = {
  release_bundle: { background: '#6366F1', border: '#4F46E5' },
  bundle: { background: '#6366F1', border: '#4F46E5' },
  platform: { background: '#8B5CF6', border: '#7C3AED' },
  client_module: { background: '#3B82F6', border: '#2563EB' },
  module: { background: '#3B82F6', border: '#2563EB' },
  admin_module: { background: '#F97316', border: '#EA580C' },
  page: { background: '#22C55E', border: '#16A34A' },
  test_case: { background: '#EF4444', border: '#DC2626' },
  business_rule: { background: '#EAB308', border: '#CA8A04' },
  api: { background: '#06B6D4', border: '#0891B2' },
}
const DEFAULT_NODE_COLOR = { background: '#64748B', border: '#475569' }

// ── Edge colors by relation type ──
const EDGE_COLORS: Record<string, { color: string; dashes: boolean }> = {
  contains: { color: '#94A3B8', dashes: false },
  belongs_to_version: { color: '#94A3B8', dashes: false },
  has_platform: { color: '#94A3B8', dashes: false },
  has_module: { color: '#94A3B8', dashes: false },
  has_page: { color: '#94A3B8', dashes: false },
  tested_by: { color: '#22C55E', dashes: true },
  navigates_to: { color: '#3B82F6', dashes: true },
  configures: { color: '#F97316', dashes: false },
  links_to_admin: { color: '#F97316', dashes: false },
  described_by: { color: '#64748B', dashes: true },
  evolves_from: { color: '#8B5CF6', dashes: true },
}
const DEFAULT_EDGE_STYLE = { color: '#94A3B8', dashes: false }

// ── Relation type labels for filter ──
const RELATION_LABELS: Record<string, string> = {
  contains: '层级',
  belongs_to_version: '层级',
  has_platform: '层级',
  has_module: '层级',
  has_page: '层级',
  tested_by: '测试',
  navigates_to: '跳转',
  configures: '配置',
  links_to_admin: '配置',
  described_by: '描述',
  evolves_from: '演化',
}

export default function SphereTab() {
  const containerRef = useRef<HTMLDivElement>(null)
  const networkRef = useRef<Network | null>(null)
  const [bundleId, setBundleId] = useState<number | undefined>(undefined)
  const [maxDepth, setMaxDepth] = useState(3)
  const [viewMode, setViewMode] = useState<'graph' | 'hierarchy' | 'list'>('graph')
  const [selectedNode, setSelectedNode] = useState<ProjectSphereNode | null>(null)
  const [hiddenTypes, setHiddenTypes] = useState<Set<string>>(new Set())

  // Fetch bundle list
  const { data: bundlePage } = useApi(
    (signal) => fetchReleaseBundles({ page_size: 200 }),
    [],
  )

  // Fetch sphere view
  const {
    data: sphere,
    isLoading,
    isError,
    refetch,
  } = useApi(
    (signal) =>
      fetchGraphHierarchy({
        release_bundle_id: bundleId,
        max_depth: maxDepth,
      }),
    [bundleId, maxDepth],
  )

  const bundles = bundlePage?.items ?? []

  // ── Build vis-network graph ──
  const buildGraph = useCallback(() => {
    if (!containerRef.current || !sphere || viewMode !== 'graph') return

    const colors = NODE_COLORS
    const edgeStyle = EDGE_COLORS

    const nodes = sphere.nodes.map((n) => ({
      id: n.id,
      label: n.name,
      group: n.node_type,
      color: colors[n.node_type] ?? DEFAULT_NODE_COLOR,
      shape: 'box',
      font: { size: 12, color: '#1e293b' },
      borderWidth: 2,
      margin: { top: 8, bottom: 8, left: 12, right: 12 },
      // Store data for click
      _nodeData: n,
    }))

    const edges = sphere.edges
      .filter((e) => {
        // Filter by hidden types
        const relGroup = RELATION_LABELS[e.relation_type] ?? e.relation_type
        return !hiddenTypes.has(relGroup)
      })
      .map((e) => {
        const style = edgeStyle[e.relation_type] ?? DEFAULT_EDGE_STYLE
        return {
          from: e.source,
          to: e.target,
          label: e.relation_type,
          color: { color: style.color, opacity: 0.7 },
          dashes: style.dashes,
          arrows: { to: { enabled: true, scaleFactor: 0.6 } },
          font: { size: 8, color: '#94a3b8', align: 'middle' },
        }
      })

    const data = { nodes: new DataSet(nodes), edges: new DataSet(edges) }
    const options = {
      layout: {
        hierarchical: {
          enabled: true,
          direction: 'UD',
          sortMethod: 'directed',
          levelSeparation: 100,
          nodeSpacing: 160,
          treeSpacing: 200,
        },
      },
      physics: { enabled: false },
      interaction: {
        hover: true,
        tooltipDelay: 200,
        navigationButtons: true,
        keyboard: true,
      },
      edges: {
        smooth: { type: 'cubicBezier', forceDirection: 'vertical' },
      },
    }

    const network = new Network(containerRef.current, data, options)

    network.on('selectNode', (params) => {
      const nodeId = params.nodes[0]
      if (nodeId) {
        const nodeData = (nodes.find((n) => n.id === nodeId) as Record<string, unknown>)?._nodeData as ProjectSphereNode
        setSelectedNode(nodeData ?? null)
      }
    })

    network.on('deselectNode', () => {
      setSelectedNode(null)
    })

    networkRef.current = network

    return () => {
      network.destroy()
      networkRef.current = null
    }
  }, [sphere, viewMode, hiddenTypes])

  useEffect(() => {
    const cleanup = buildGraph()
    return () => cleanup?.()
  }, [buildGraph])

  // Toggle edge type filter
  const toggleRelationFilter = (relationGroup: string) => {
    setHiddenTypes((prev) => {
      const next = new Set(prev)
      if (next.has(relationGroup)) next.delete(relationGroup)
      else next.add(relationGroup)
      return next
    })
  }

  // Collect unique relation groups for filter
  const relationGroups = useMemo(() => {
    if (!sphere) return []
    const groups = new Set<string>()
    for (const e of sphere.edges) {
      groups.add(RELATION_LABELS[e.relation_type] ?? e.relation_type)
    }
    return Array.from(groups)
  }, [sphere])

  return (
    <div className="space-y-4">
      {/* Controls */}
      <div className="flex items-center gap-3 flex-wrap">
        <Select
          value={bundleId ? String(bundleId) : 'all'}
          onValueChange={(v) =>
            setBundleId(v === 'all' ? undefined : Number(v))
          }
        >
          <SelectTrigger className="w-[280px] h-9 text-sm">
            <SelectValue placeholder="选择发布包（全部）" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">全部发布包</SelectItem>
            {bundles.map((b) => (
              <SelectItem key={b.id} value={String(b.id)}>
                {b.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Select
          value={String(maxDepth)}
          onValueChange={(v) => setMaxDepth(Number(v))}
        >
          <SelectTrigger className="w-[110px] h-9 text-sm">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="2">深度 2</SelectItem>
            <SelectItem value="3">深度 3</SelectItem>
            <SelectItem value="4">深度 4</SelectItem>
          </SelectContent>
        </Select>

        <ToggleGroup
          type="single"
          value={viewMode}
          onValueChange={(v) => v && setViewMode(v as 'graph' | 'hierarchy' | 'list')}
        >
          <ToggleGroupItem value="graph" size="sm">
            <GitGraph className="h-4 w-4 mr-1" /> 图谱
          </ToggleGroupItem>
          <ToggleGroupItem value="list" size="sm">
            <List className="h-4 w-4 mr-1" /> 列表
          </ToggleGroupItem>
        </ToggleGroup>

        <Button variant="outline" size="sm" onClick={() => refetch()} disabled={isLoading}>
          <RefreshCw className={cn('size-4 mr-1', isLoading && 'animate-spin')} />
          刷新
        </Button>
      </div>

      {/* Edge filter toggles (graph mode) */}
      {viewMode === 'graph' && relationGroups.length > 0 && (
        <div className="flex items-center gap-1.5 flex-wrap">
          <span className="text-xs text-muted-foreground mr-1">边筛选:</span>
          {relationGroups.map((group) => (
            <Badge
              key={group}
              variant={hiddenTypes.has(group) ? 'outline' : 'default'}
              className="text-xs cursor-pointer"
              onClick={() => toggleRelationFilter(group)}
            >
              {group}
            </Badge>
          ))}
        </div>
      )}

      {/* Stats */}
      {sphere && (
        <div className="grid grid-cols-6 gap-2">
          {Object.entries(sphere.stats ?? {}).map(([key, value]) => (
            <Card key={key}>
              <CardContent className="p-2 text-center">
                <div className="text-lg font-bold">{String(value)}</div>
                <div className="text-[10px] text-muted-foreground">{key}</div>
              </CardContent>
            </Card>
          ))}
          <Card>
            <CardContent className="p-2 text-center">
              <div className="text-lg font-bold">{sphere.nodes.length}</div>
              <div className="text-[10px] text-muted-foreground">节点</div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-2 text-center">
              <div className="text-lg font-bold">{sphere.edges.length}</div>
              <div className="text-[10px] text-muted-foreground">关系</div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Loading / Error */}
      {isLoading && (
        <div className="text-center py-12 text-muted-foreground">
          <RefreshCw className="size-8 mx-auto mb-2 animate-spin opacity-40" />
          <p className="text-sm">加载项目球图谱...</p>
        </div>
      )}
      {isError && (
        <div className="text-center py-12 text-muted-foreground">
          <p className="text-sm">加载失败</p>
          <Button variant="outline" size="sm" className="mt-2" onClick={() => refetch()}>
            重试
          </Button>
        </div>
      )}

      {/* Graph View */}
      {sphere && !isLoading && !isError && viewMode === 'graph' && (
        <div className="flex gap-4">
          {/* Graph container */}
          <div className="flex-1">
            <div
              ref={containerRef}
              className="w-full rounded-lg border bg-card"
              style={{ height: '550px' }}
            />
          </div>

          {/* Detail panel */}
          {selectedNode && (
            <Card className="w-72 shrink-0">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm">{selectedNode.name}</CardTitle>
              </CardHeader>
              <CardContent className="space-y-1 text-xs">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">类型</span>
                  <Badge
                    variant="outline"
                    className="text-[10px]"
                    style={{
                      backgroundColor: (NODE_COLORS[selectedNode.node_type] ?? DEFAULT_NODE_COLOR).background + '20',
                      borderColor: (NODE_COLORS[selectedNode.node_type] ?? DEFAULT_NODE_COLOR).border,
                    }}
                  >
                    {selectedNode.node_type}
                  </Badge>
                </div>
                {selectedNode.platform && (
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">平台</span>
                    <span>{selectedNode.platform}</span>
                  </div>
                )}
                {selectedNode.version && (
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">版本</span>
                    <span>{selectedNode.version}</span>
                  </div>
                )}
                {selectedNode.change_type && selectedNode.change_type !== 'unchanged' && (
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">变更</span>
                    <Badge
                      variant="outline"
                      className={cn(
                        'text-xs',
                        selectedNode.change_type === 'new' && 'border-green-200 text-green-700',
                        selectedNode.change_type === 'modified' && 'border-yellow-200 text-yellow-700',
                        selectedNode.change_type === 'deleted' && 'border-red-200 text-red-700',
                      )}
                    >
                      {selectedNode.change_type}
                    </Badge>
                  </div>
                )}
                {selectedNode.description && (
                  <p className="text-muted-foreground mt-2">{selectedNode.description}</p>
                )}
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {/* List View (compact) */}
      {sphere && !isLoading && !isError && viewMode === 'list' && (
        <div className="space-y-4">
          {/* Edges list */}
          {sphere.edges.length > 0 && (
            <Card>
              <CardHeader className="py-2 px-3">
                <CardTitle className="text-xs font-medium">
                  关系列表 ({sphere.edges.length})
                </CardTitle>
              </CardHeader>
              <CardContent className="p-0 max-h-[500px] overflow-auto">
                <div className="divide-y">
                  {sphere.edges.slice(0, 200).map((edge, idx) => {
                    const sourceNode = sphere.nodes.find((n) => n.id === edge.source)
                    const targetNode = sphere.nodes.find((n) => n.id === edge.target)
                    if (!sourceNode || !targetNode) return null
                    const edgeCfg = EDGE_COLORS[edge.relation_type] ?? DEFAULT_EDGE_STYLE
                    return (
                      <div
                        key={idx}
                        className="flex items-center gap-1.5 px-3 py-1.5 text-xs hover:bg-muted/40"
                      >
                        <span className="font-medium truncate max-w-[180px]">
                          {sourceNode.platform && (
                            <span className="mr-1">
                              {sourceNode.platform === 'APP' ? '📱' : sourceNode.platform === 'PC' ? '🖥' : sourceNode.platform === 'WEB' ? '🌐' : '⚙️'}
                            </span>
                          )}
                          {sourceNode.name}
                        </span>
                        <ArrowRight className="size-3 text-muted-foreground shrink-0" />
                        <Badge
                          variant="outline"
                          className="text-[9px] px-1 py-0 shrink-0"
                          style={{ color: edgeCfg.color, borderColor: edgeCfg.color }}
                        >
                          {edge.relation_type}
                        </Badge>
                        <ArrowRight className="size-3 text-muted-foreground shrink-0" />
                        <span className="font-medium truncate max-w-[180px]">
                          {targetNode.platform && (
                            <span className="mr-1">
                              {targetNode.platform === 'APP' ? '📱' : targetNode.platform === 'PC' ? '🖥' : targetNode.platform === 'WEB' ? '🌐' : '⚙️'}
                            </span>
                          )}
                          {targetNode.name}
                        </span>
                      </div>
                    )
                  })}
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {/* Empty state */}
      {!sphere && !isLoading && !isError && (
        <div className="text-center py-16 text-muted-foreground">
          <Layers className="size-16 mx-auto mb-4 opacity-20" />
          <p className="font-medium">项目球知识图谱</p>
          <p className="text-sm mt-1">
            选择发布包，查看项目→版本→平台→模块→页面的层级图谱
          </p>
        </div>
      )}
    </div>
  )
}
