import { useCallback, useEffect, useRef, useState } from 'react'
import { Network } from 'vis-network'
import { DataSet } from 'vis-data'
import { toast } from 'sonner'
import { RefreshCw, Maximize2, Plus, MinusCircle } from '@/lib/icons'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { SkeletonText } from '@/components/ui/skeleton'
import { fetchGraphView, triggerEntityExtract } from '@/api/knowledge'
import type { GraphView } from '@/types'

// ── 实体类型着色 ──
const GROUP_COLORS: Record<string, string> = {
  api: '#3b82f6',
  field: '#10b981',
  requirement: '#8b5cf6',
  test_case: '#f59e0b',
  defect: '#ef4444',
}
const DEFAULT_COLOR = '#6b7280'

// ── 关系类型样式 ──
const EDGE_DASHES: Record<string, boolean> = {
  contains: false,
  executed_by: true,
  depends_on: true,
  affects: true,
  covers: true,
  generated_from: true,
}

const TYPE_LABELS: Record<string, string> = {
  api: 'API',
  field: '字段',
  requirement: '需求',
  test_case: '用例',
  defect: '缺陷',
}

export default function GraphTab() {
  const containerRef = useRef<HTMLDivElement>(null)
  const networkRef = useRef<Network | null>(null)
  const [graphData, setGraphData] = useState<GraphView | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selected, setSelected] = useState<{ id: string; name: string; type: string; description: string; confidence: number } | null>(null)
  const [extracting, setExtracting] = useState(false)
  const [hiddenTypes, setHiddenTypes] = useState<Set<string>>(new Set())

  const loadGraph = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await fetchGraphView(200)
      setGraphData(data)
    } catch (e: any) {
      setError(e?.message || '加载图谱数据失败')
    } finally {
      setLoading(false)
    }
  }, [])

  // 初始加载
  useEffect(() => {
    loadGraph()
  }, [loadGraph])

  // 渲染 vis-network
  useEffect(() => {
    if (!graphData || !containerRef.current) return

    // 销毁旧实例
    if (networkRef.current) {
      networkRef.current.destroy()
      networkRef.current = null
    }

    // 计算每个节点的度（关联边数）
    const degreeMap: Record<string, number> = {}
    for (const e of graphData.edges) {
      degreeMap[e.source] = (degreeMap[e.source] || 0) + 1
      degreeMap[e.target] = (degreeMap[e.target] || 0) + 1
    }
    const minSize = 16
    const maxSize = 45
    const maxDegree = Math.max(1, ...Object.values(degreeMap))

    const nodes = new DataSet(
      graphData.nodes.map((n) => {
        const degree = degreeMap[n.id] || 0
        const scale = degree / maxDegree
        const size = minSize + scale * (maxSize - minSize)
        return {
          id: n.id,
          label: n.name.length > 20 ? n.name.slice(0, 18) + '…' : n.name,
          title: `<b>${n.name}</b><br/>${n.description || ''}<br/>置信度: ${(n.confidence * 100).toFixed(0)}%<br/>关联: ${degree} 条边`,
          group: n.group,
          color: {
            background: GROUP_COLORS[n.entity_type] || DEFAULT_COLOR,
            border: '#fff',
            highlight: {
              background: GROUP_COLORS[n.entity_type] || DEFAULT_COLOR,
              border: '#333',
            },
          },
          font: { color: '#fff', size: Math.max(11, Math.round(13 * (1 + scale * 0.3))) },
          shape: 'dot',
          size,
          entityType: n.entity_type,
          description: n.description,
          confidence: n.confidence,
          entityId: n.entity_id,
        }
      })
    )

    const edges = new DataSet(
      graphData.edges.map((e, i) => ({
        id: `e${i}`,
        from: e.source,
        to: e.target,
        label: e.relation_type,
        title: `${e.relation_type} (${(e.confidence * 100).toFixed(0)}%)`,
        dashes: EDGE_DASHES[e.relation_type] ?? false,
        arrows: 'to',
        color: { color: '#94a3b8', highlight: '#64748b' },
        width: 1.5,
        font: { size: 10, color: '#64748b', strokeWidth: 0 },
      }))
    )

    const network = new Network(containerRef.current, { nodes, edges }, {
      physics: {
        solver: 'forceAtlas2Based',
        forceAtlas2Based: {
          gravitationalConstant: -30,
          centralGravity: 0.005,
          springLength: 120,
          springConstant: 0.08,
        },
        stabilization: {
          iterations: 150,
        },
      },
      interaction: {
        hover: true,
        tooltipDelay: 200,
        zoomView: true,
        dragView: true,
      },
      nodes: {
        borderWidth: 2,
        shadow: { enabled: true, size: 6 },
      },
      edges: {
        smooth: { enabled: true, type: 'continuous', roundness: 0.5 },
        hoverWidth: 2,
      },
    })

    // 节点点击 → 选中详览
    network.on('selectNode', (params: any) => {
      const nodeId = params.nodes[0]
      const node = nodes.get(nodeId) as any
      if (node) {
        setSelected({
          id: nodeId,
          name: node.label,
          type: node.entityType || '',
          description: node.description || '',
          confidence: node.confidence || 0,
        })
      }
    })

    network.on('deselectNode', () => {
      setSelected(null)
    })

    networkRef.current = network

    return () => {
      network.destroy()
      networkRef.current = null
    }
  }, [graphData])

  // 按类型过滤节点可见性
  useEffect(() => {
    if (!networkRef.current) return
    const allNodes = (networkRef.current as any).body.data.nodes
    allNodes.forEach((node: any) => {
      const entityType = node.entityType || ''
      const shouldHide = hiddenTypes.has(entityType)
      allNodes.update({ id: node.id, hidden: shouldHide })
    })
  }, [hiddenTypes])

  const handleExtract = async () => {
    setExtracting(true)
    try {
      const result = await triggerEntityExtract(null, 100)
      toast.success(result.message || `提取完成：${result.extracted} 实体 + ${result.relations} 关系`)
      loadGraph()
    } catch (e: any) {
      toast.error(e?.message || '提取失败')
    } finally {
      setExtracting(false)
    }
  }

  // ── Loading ──
  if (loading) {
    return (
      <div className="space-y-3 p-4">
        <SkeletonText />
        <SkeletonText />
        <SkeletonText />
        <SkeletonText />
      </div>
    )
  }

  // ── Error ──
  if (error) {
    return (
      <div className="flex flex-col items-center justify-center py-20 gap-3">
        <p className="text-sm text-muted-foreground">{error}</p>
        <Button variant="outline" size="sm" onClick={loadGraph}>
          <RefreshCw className="size-4 mr-1" />
          重试
        </Button>
      </div>
    )
  }

  // ── Empty ──
  if (!graphData || graphData.nodes.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-20 gap-4">
        <p className="text-sm text-muted-foreground">暂无图谱数据，请先提取实体与关系</p>
        <Button onClick={handleExtract} disabled={extracting}>
          {extracting ? (
            <>
              <RefreshCw className="size-4 mr-1 animate-spin" />
              提取中…
            </>
          ) : (
            <>
              <RefreshCw className="size-4 mr-1" />
              触发实体提取
            </>
          )}
        </Button>
      </div>
    )
  }

  // ── 主视图 ──
  return (
    <div className="flex gap-4 p-4" style={{ height: 'calc(100vh - 260px)' }}>
      {/* 图谱画布 */}
      <div className="flex-1 relative rounded-lg border overflow-hidden bg-background">
        {/* 工具栏 */}
        <div className="absolute top-2 right-2 z-10 flex gap-1">
          <Button
            variant="secondary"
            size="icon"
            className="size-8"
            onClick={() => networkRef.current?.moveTo({ scale: (networkRef.current as any)?.getScale?.() * 1.3 || 1.3 })}
            title="放大"
          >
            <Plus className="size-4" />
          </Button>
          <Button
            variant="secondary"
            size="icon"
            className="size-8"
            onClick={() => networkRef.current?.moveTo({ scale: (networkRef.current as any)?.getScale?.() * 0.7 || 0.7 })}
            title="缩小"
          >
            <MinusCircle className="size-4" />
          </Button>
          <Button
            variant="secondary"
            size="icon"
            className="size-8"
            onClick={() => networkRef.current?.fit({ animation: true })}
            title="适应画布"
          >
            <Maximize2 className="size-4" />
          </Button>
          <Button
            variant="secondary"
            size="sm"
            onClick={handleExtract}
            disabled={extracting}
            title="重新提取"
          >
            <RefreshCw className={`size-4 mr-1 ${extracting ? 'animate-spin' : ''}`} />
            提取
          </Button>
        </div>

        {/* vis 容器 */}
        <div ref={containerRef} className="w-full h-full" />
      </div>

      {/* 详情面板 */}
      <div className="w-64 shrink-0">
        {selected ? (
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm">{selected.name}</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-sm">
              <div className="flex items-center gap-2">
                <span className="text-muted-foreground">类型</span>
                <Badge variant="secondary">
                  {TYPE_LABELS[selected.type] || selected.type}
                </Badge>
              </div>
              {selected.description && (
                <div>
                  <span className="text-muted-foreground">描述</span>
                  <p className="text-xs mt-0.5">{selected.description}</p>
                </div>
              )}
              <div>
                <span className="text-muted-foreground">置信度</span>
                <p className="text-xs font-mono">{(selected.confidence * 100).toFixed(0)}%</p>
              </div>
            </CardContent>
          </Card>
        ) : (
          <div className="flex flex-col gap-3">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm">图例 <span className="text-xs font-normal text-muted-foreground">(点击过滤)</span></CardTitle>
              </CardHeader>
              <CardContent className="space-y-1.5">
                {Object.entries(TYPE_LABELS).map(([key, label]) => {
                  const hidden = hiddenTypes.has(key)
                  return (
                    <div
                      key={key}
                      className={`flex items-center gap-2 text-sm cursor-pointer rounded px-1 py-0.5 hover:bg-muted/50 transition-colors ${hidden ? 'opacity-40' : ''}`}
                      onClick={() => {
                        setHiddenTypes((prev) => {
                          const next = new Set(prev)
                          if (next.has(key)) next.delete(key)
                          else next.add(key)
                          return next
                        })
                      }}
                    >
                      <span
                        className="inline-block size-3 rounded-full shrink-0"
                        style={{ backgroundColor: GROUP_COLORS[key] || DEFAULT_COLOR }}
                      />
                      <span className={`text-muted-foreground ${hidden ? 'line-through' : ''}`}>{label}</span>
                      <span className="text-xs text-muted-foreground/60 ml-auto">
                        {graphData.nodes.filter((n) => n.entity_type === key).length}
                      </span>
                    </div>
                  )
                })}
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm">统计</CardTitle>
              </CardHeader>
              <CardContent className="space-y-1 text-sm text-muted-foreground">
                <p>节点 {graphData.nodes.filter((n) => !hiddenTypes.has(n.entity_type)).length}/{graphData.nodes.length}</p>
                <p>边 {graphData.edges.length}</p>
              </CardContent>
            </Card>
          </div>
        )}
      </div>
    </div>
  )
}
