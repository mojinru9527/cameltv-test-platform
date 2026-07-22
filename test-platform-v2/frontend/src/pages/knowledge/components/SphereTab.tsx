import { useState, useMemo } from 'react'
import { toast } from 'sonner'
import { fetchGraphHierarchy } from '@/api/knowledge'
import { fetchReleaseBundles } from '@/api/releaseBundles'
import type { ProjectSphereView, ProjectSphereNode, ProjectSphereEdge } from '@/types'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Layers,
  RefreshCw,
  Box,
  FileText,
  Package,
  FolderOpen,
  Paperclip,
  GitBranch,
  Monitor,
  Smartphone,
  Globe,
  Shield,
  ArrowRight,
} from '@/lib/icons'
import { cn } from '@/lib/utils'
import { useApi } from '@/hooks/useApi'

const NODE_TYPE_COLORS: Record<string, string> = {
  project: 'border-blue-300 bg-blue-50 text-blue-700',
  version: 'border-purple-300 bg-purple-50 text-purple-700',
  platform: 'border-cyan-300 bg-cyan-50 text-cyan-700',
  module: 'border-green-300 bg-green-50 text-green-700',
  page: 'border-amber-300 bg-amber-50 text-amber-700',
  attachment: 'border-gray-300 bg-gray-50 text-gray-700',
  admin_module: 'border-red-300 bg-red-50 text-red-700',
}

const RELATION_COLORS: Record<string, string> = {
  contains: 'text-blue-600 bg-blue-50',
  configures: 'text-purple-600 bg-purple-50',
  tested_by: 'text-green-600 bg-green-50',
  navigates_to: 'text-amber-600 bg-amber-50',
  described_by: 'text-gray-600 bg-gray-50',
}

export default function SphereTab() {
  const [bundleId, setBundleId] = useState<number | undefined>(undefined)
  const [maxDepth, setMaxDepth] = useState(3)

  // ── Fetch bundle list for picker ──
  const { data: bundlePage } = useApi(
    (signal) => fetchReleaseBundles({ page_size: 200 }),
    [],
  )

  // ── Fetch sphere view ──
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

  // ── Organize nodes by type ──
  const nodesByType = useMemo(() => {
    if (!sphere) return {}
    const groups: Record<string, ProjectSphereNode[]> = {}
    for (const node of sphere.nodes) {
      const t = node.node_type
      if (!groups[t]) groups[t] = []
      groups[t].push(node)
    }
    return groups
  }, [sphere])

  // ── Relation stats ──
  const relationStats = useMemo(() => {
    if (!sphere) return {}
    const counts: Record<string, number> = {}
    for (const edge of sphere.edges) {
      counts[edge.relation_type] = (counts[edge.relation_type] ?? 0) + 1
    }
    return counts
  }, [sphere])

  return (
    <div className="space-y-4">
      {/* ── Controls ── */}
      <div className="flex items-center gap-3">
        <Select
          value={bundleId ? String(bundleId) : 'all'}
          onValueChange={(v) =>
            setBundleId(v === 'all' ? undefined : Number(v))
          }
        >
          <SelectTrigger className="w-[300px] h-9 text-sm">
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
          <SelectTrigger className="w-[120px] h-9 text-sm">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="2">深度 2</SelectItem>
            <SelectItem value="3">深度 3</SelectItem>
            <SelectItem value="4">深度 4</SelectItem>
          </SelectContent>
        </Select>

        <Button variant="outline" size="sm" onClick={() => refetch()} disabled={isLoading}>
          <RefreshCw className={cn('size-4 mr-1', isLoading && 'animate-spin')} />
          刷新
        </Button>
      </div>

      {/* ── Stats ── */}
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
              <div className="text-[10px] text-muted-foreground">节点总数</div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-2 text-center">
              <div className="text-lg font-bold">{sphere.edges.length}</div>
              <div className="text-[10px] text-muted-foreground">关系总数</div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* ── Loading / Error ── */}
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

      {/* ── Hierarchy view ── */}
      {sphere && !isLoading && !isError && (
        <div className="space-y-4">
          {/* Nodes by layer */}
          {Object.entries(nodesByType).map(([nodeType, nodes]) => (
            <Card key={nodeType}>
              <CardHeader className="py-2 px-3">
                <CardTitle className="text-xs font-medium flex items-center gap-2">
                  <Badge
                    variant="outline"
                    className={cn('text-[10px]', NODE_TYPE_COLORS[nodeType] ?? '')}
                  >
                    {nodeType}
                  </Badge>
                  <span className="text-muted-foreground">{nodes.length} 个</span>
                </CardTitle>
              </CardHeader>
              <CardContent className="p-0">
                <div className="flex flex-wrap gap-1 px-3 pb-3">
                  {nodes.map((node) => (
                    <Badge
                      key={node.id}
                      variant="secondary"
                      className="text-[11px] max-w-[200px] truncate"
                      title={`${node.name}${node.version ? ` (v${node.version})` : ''}${node.platform ? ` [${node.platform}]` : ''}`}
                    >
                      {node.platform && (
                        <span className="mr-1">
                          {node.platform === 'APP' ? '📱' : node.platform === 'PC' ? '🖥' : node.platform === 'WEB' ? '🌐' : '⚙️'}
                        </span>
                      )}
                      {node.name}
                      {node.change_type && node.change_type !== 'unchanged' && (
                        <span className="ml-1 text-[9px] opacity-60">
                          ({node.change_type === 'new' ? '新增' : node.change_type === 'modified' ? '变更' : '删除'})
                        </span>
                      )}
                    </Badge>
                  ))}
                </div>
              </CardContent>
            </Card>
          ))}

          {/* Relations summary */}
          {Object.keys(relationStats).length > 0 && (
            <Card>
              <CardHeader className="py-2 px-3">
                <CardTitle className="text-xs font-medium">关系类型分布</CardTitle>
              </CardHeader>
              <CardContent className="px-3 pb-3">
                <div className="flex flex-wrap gap-2">
                  {Object.entries(relationStats).map(([relType, count]) => (
                    <Badge
                      key={relType}
                      variant="outline"
                      className={cn('text-[11px] gap-1', RELATION_COLORS[relType] ?? '')}
                    >
                      {relType}
                      <span className="font-bold">{count}</span>
                    </Badge>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Edge list (compact) */}
          {sphere.edges.length > 0 && (
            <Card>
              <CardHeader className="py-2 px-3">
                <CardTitle className="text-xs font-medium">
                  关系列表 ({sphere.edges.length})
                </CardTitle>
              </CardHeader>
              <CardContent className="p-0 max-h-[400px] overflow-auto">
                <div className="divide-y">
                  {sphere.edges.slice(0, 100).map((edge, idx) => {
                    const sourceNode = sphere.nodes.find((n) => n.id === edge.source)
                    const targetNode = sphere.nodes.find((n) => n.id === edge.target)
                    if (!sourceNode || !targetNode) return null
                    return (
                      <div
                        key={idx}
                        className="flex items-center gap-1.5 px-3 py-1.5 text-xs hover:bg-muted/40"
                      >
                        <span className="font-medium truncate max-w-[180px]">
                          {sourceNode.name}
                        </span>
                        <ArrowRight className="size-3 text-muted-foreground shrink-0" />
                        <Badge
                          variant="outline"
                          className={cn(
                            'text-[9px] px-1 py-0 shrink-0',
                            RELATION_COLORS[edge.relation_type] ?? '',
                          )}
                        >
                          {edge.relation_type}
                        </Badge>
                        <ArrowRight className="size-3 text-muted-foreground shrink-0" />
                        <span className="font-medium truncate max-w-[180px]">
                          {targetNode.name}
                        </span>
                        {edge.confidence < 1 && (
                          <span className="text-[9px] text-muted-foreground ml-auto">
                            {Math.round(edge.confidence * 100)}%
                          </span>
                        )}
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
