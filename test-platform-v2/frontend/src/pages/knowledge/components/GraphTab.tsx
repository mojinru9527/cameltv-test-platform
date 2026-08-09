import { useCallback, useEffect, useRef, useState } from 'react'
import { Network } from 'vis-network'
import { DataSet } from 'vis-data'
import { toast } from 'sonner'
import { RefreshCw, Maximize2, Plus, MinusCircle, GitMerge } from '@/lib/icons'
import { Button } from '@/ui'
import { Badge } from '@/ui'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { SkeletonText } from '@/components/ui/skeleton'
import { fetchGraphView, triggerEntityExtract, evolveGraph } from '@/api/knowledge'
import type { GraphEvolveResult } from '@/api/knowledge'
import type { GraphView } from '@/types'

// ── 实体类型着色 ──
const GROUP_COLORS: Record<string, string> = {
  module: '#8b5cf6',
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
  tested_by: false,
  navigates_to: false,
  configures: true,
  links_to_admin: true,
  evolves_from: true,
  described_by: true,
}

// ── 关系类型中文标签（图例） ──
const RELATION_LABELS: Record<string, string> = {
  contains: '包含（层级）',
  tested_by: '被用例覆盖',
  navigates_to: '跳转关联',
  configures: '配置影响',
  links_to_admin: '对应后台管理',
  evolves_from: '版本演化',
  executed_by: '执行来源',
  depends_on: '依赖',
  affects: '影响',
  covers: '覆盖',
  generated_from: '生成自',
  described_by: '描述',
}

const TYPE_LABELS: Record<string, string> = {
  module: '模块',
  api: 'API',
  field: '字段',
  requirement: '需求',
  test_case: '用例',
  defect: '缺陷',
}

export default function GraphTab() {
  const containerRef = useRef<HTMLDivElement>(null)
  const networkRef = useRef<Network | null>(null)
  const loadControllerRef = useRef<AbortController | null>(null)
  const [graphData, setGraphData] = useState<GraphView | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selected, setSelected] = useState<{ id: string; name: string; type: string; description: string; confidence: number } | null>(null)
  const [extracting, setExtracting] = useState(false)
  const [hiddenTypes, setHiddenTypes] = useState<Set<string>>(new Set())
  const [evolving, setEvolving] = useState(false)
  const [evolveResult, setEvolveResult] = useState<GraphEvolveResult | null>(null)
  const [domain, setDomain] = useState<string>('project')
  const extractUnavailableReason = graphData?.unavailable_reason || '当前没有可提取的知识片段'

  const loadGraph = useCallback(async (d?: string) => {
    const dom = d ?? domain
    loadControllerRef.current?.abort()
    const controller = new AbortController()
    loadControllerRef.current = controller
    setLoading(true)
    setError(null)
    try {
      const data = await fetchGraphView(1000, dom, controller.signal)
      if (controller.signal.aborted) return
      setGraphData(data)
    } catch (e: any) {
      if (controller.signal.aborted) return
      setError(e?.message || '加载图谱数据失败')
    } finally {
      if (!controller.signal.aborted) setLoading(false)
    }
  }, [domain])

  // 初始加载
  useEffect(() => {
    loadGraph()
    return () => loadControllerRef.current?.abort()
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

  const handleEvolve = async () => {
    setEvolving(true)
    setEvolveResult(null)
    try {
      const result = await evolveGraph()
      setEvolveResult(result)
      toast.success(result.message || '演化完成')
      loadGraph()
    } catch (e: any) {
      toast.error(e?.message || '演化失败')
    } finally {
      setEvolving(false)
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
        <Button variant="secondary" size="sm" onClick={() => loadGraph()}>
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
        <div className="max-w-xl space-y-1 text-center">
          <p className="text-sm font-medium">暂无图谱数据</p>
          <p className="text-sm text-muted-foreground">
            {graphData?.extract_available ? '可以从当前知识片段提取实体与关系' : extractUnavailableReason}
          </p>
        </div>
        <Button
          onClick={handleExtract}
          disabled={extracting || !graphData?.extract_available}
          title={graphData?.extract_available ? '触发实体提取' : extractUnavailableReason}
        >
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
    <div className="flex min-h-[calc(100dvh-260px)] flex-col gap-4 p-3 sm:p-4 lg:h-[calc(100dvh-260px)] lg:flex-row">
      {/* 图谱画布 */}
      <div className="relative min-h-[420px] min-w-0 flex-1 overflow-hidden rounded-lg border bg-background">
        {/* 工具栏 */}
        <div className="absolute inset-x-2 top-2 z-10 flex max-h-[132px] flex-wrap justify-end gap-1 overflow-auto rounded-lg bg-background/92 p-1 backdrop-blur-sm">
          {/* 知识域切换 */}
          <div className="flex rounded-md border bg-background mr-1">
            <button
              type="button"
              className={`px-2 py-1 text-xs rounded-l-md transition-colors ${domain === 'project' ? 'bg-primary text-primary-foreground' : 'hover:bg-muted'}`}
              onClick={() => { setDomain('project'); loadGraph('project') }}
              aria-pressed={domain === 'project'}
            >
              项目知识
            </button>
            <button
              type="button"
              className={`px-2 py-1 text-xs rounded-r-md transition-colors ${domain === 'platform' ? 'bg-primary text-primary-foreground' : 'hover:bg-muted'}`}
              onClick={() => { setDomain('platform'); loadGraph('platform') }}
              aria-pressed={domain === 'platform'}
            >
              平台研发
            </button>
          </div>
          <Button
            variant="secondary"
            size="icon"
            className="size-8"
            onClick={() => networkRef.current?.moveTo({ scale: (networkRef.current as any)?.getScale?.() * 1.3 || 1.3 })}
            aria-label="放大知识图谱"
          >
            <Plus className="size-4" aria-hidden="true" />
          </Button>
          <Button
            variant="secondary"
            size="icon"
            className="size-8"
            onClick={() => networkRef.current?.moveTo({ scale: (networkRef.current as any)?.getScale?.() * 0.7 || 0.7 })}
            aria-label="缩小知识图谱"
          >
            <MinusCircle className="size-4" aria-hidden="true" />
          </Button>
          <Button
            variant="secondary"
            size="icon"
            className="size-8"
            onClick={() => networkRef.current?.fit({ animation: true })}
            aria-label="让知识图谱适应画布"
          >
            <Maximize2 className="size-4" aria-hidden="true" />
          </Button>
          <Button
            variant="secondary"
            size="sm"
            onClick={handleExtract}
            disabled={extracting || !graphData.extract_available}
            title={graphData.extract_available ? '重新提取' : extractUnavailableReason}
          >
            <RefreshCw className={`size-4 mr-1 ${extracting ? 'animate-spin' : ''}`} />
            提取
          </Button>
          <Button
            variant="secondary"
            size="sm"
            onClick={handleEvolve}
            disabled={evolving}
            title="概念地图自演化：合并重复实体、发现隐含关系"
          >
            <GitMerge className={`size-4 mr-1 ${evolving ? 'animate-spin' : ''}`} />
            演化
          </Button>
        </div>

        {/* vis 容器 */}
        <div
          ref={containerRef}
          className="w-full h-full"
          role="img"
          aria-label={`知识图谱，共 ${graphData.nodes.length} 个节点、${graphData.edges.length} 条关系`}
        />
      </div>

      {/* 详情面板 */}
      <div className="w-full shrink-0 lg:w-64">
        {selected ? (
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm">{selected.name}</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-sm">
              <div className="flex items-center gap-2">
                <span className="text-muted-foreground">类型</span>
                <Badge tone="neutral">
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
                    <button
                      type="button"
                      key={key}
                      className={`flex w-full items-center gap-2 rounded px-2 py-1 text-left text-sm transition-colors hover:bg-muted/50 ${hidden ? 'opacity-40' : ''}`}
                      onClick={() => {
                        setHiddenTypes((prev) => {
                          const next = new Set(prev)
                          if (next.has(key)) next.delete(key)
                          else next.add(key)
                          return next
                        })
                      }}
                      aria-pressed={!hidden}
                    >
                      <span
                        className="inline-block size-3 rounded-full shrink-0"
                        style={{ backgroundColor: GROUP_COLORS[key] || DEFAULT_COLOR }}
                      />
                      <span className={`text-muted-foreground ${hidden ? 'line-through' : ''}`}>{label}</span>
                      <span className="text-xs text-muted-foreground/60 ml-auto">
                        {graphData.nodes.filter((n) => n.entity_type === key).length}
                      </span>
                    </button>
                  )
                })}
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm">关系类型</CardTitle>
              </CardHeader>
              <CardContent className="space-y-1">
                {Object.entries(RELATION_LABELS).map(([key, label]) => (
                  <div key={key} className="flex items-center gap-2 text-sm text-muted-foreground">
                    <span
                      className="inline-block h-0.5 w-4 shrink-0 rounded"
                      style={{ backgroundColor: EDGE_DASHES[key] === false ? '#94a3b8' : '#64748b' }}
                    />
                    <span>{label}</span>
                    <span className="text-xs text-muted-foreground/60 ml-auto">
                      {graphData.edges.filter((e) => e.relation_type === key).length}
                    </span>
                  </div>
                ))}
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm">统计</CardTitle>
              </CardHeader>
              <CardContent className="space-y-1 text-sm text-muted-foreground">
                <p>节点 {graphData.nodes.filter((n) => !hiddenTypes.has(n.entity_type)).length}/{graphData.nodes.length}</p>
                {graphData.nodes.length > 400 && (
                  <p className="text-xs text-status-warning">图谱数据量较大（{graphData.nodes.length} 节点），渲染可能较慢；建议按「项目知识/平台研发」域过滤查看。</p>
                )}
                <p>边 {graphData.edges.length}</p>
              </CardContent>
            </Card>

            {evolveResult && (
              <Card className="border-primary/30">
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm flex items-center gap-1.5">
                    <GitMerge className="size-4 text-primary" />
                    演化结果
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-1 text-sm text-muted-foreground">
                  {evolveResult.merged > 0 && (
                    <p>合并重复实体: <span className="font-medium text-foreground">{evolveResult.merged}</span></p>
                  )}
                  {evolveResult.confidence_updates > 0 && (
                    <p>更新置信度: <span className="font-medium text-foreground">{evolveResult.confidence_updates}</span></p>
                  )}
                  {evolveResult.new_relations > 0 && (
                    <p>新隐含关系: <span className="font-medium text-foreground">{evolveResult.new_relations}</span></p>
                  )}
                  {evolveResult.merged === 0 && evolveResult.new_relations === 0 && (
                    <p className="text-xs">图谱已是最优状态，无需演化</p>
                  )}
                </CardContent>
              </Card>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
