import { Badge, Skeleton } from '@/ui'
import type { EntityGraphResult, EntityNode } from '@/api/production'
import { GitBranch, GitCompare } from '@/lib/icons'

interface EntityGraphViewerProps {
  graph: EntityGraphResult | null
  loading?: boolean
}

function NodePill({ node }: { node: EntityNode }) {
  const label = node.label ?? node.entity_type ?? node.id
  return (
    <span className="inline-flex items-center gap-1 rounded-full border bg-muted/30 px-2 py-0.5 font-mono text-xs">
      {typeof label === 'string' ? label : node.id}
      {node.ref_hash && (
        <span className="text-muted-foreground" title={node.ref_hash}>·{node.ref_hash.slice(0, 8)}</span>
      )}
    </span>
  )
}

/** Render an extracted entity graph (nodes + edges) as a simple network / list. */
export function EntityGraphViewer({ graph, loading = false }: EntityGraphViewerProps) {
  if (loading) return <Skeleton className="h-32 w-full" />
  if (!graph) return <p className="py-4 text-sm text-muted-foreground">暂无实体图谱。先执行「提取实体图谱」。</p>

  const nodes = graph.nodes ?? []
  const edges = graph.edges ?? []

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
        <GitBranch className="size-3.5" />
        <span className="font-medium">图谱 #{graph.id}</span>
        <Badge tone="neutral" className="font-mono">{nodes.length} 节点</Badge>
        <Badge tone="neutral" className="font-mono">{edges.length} 边</Badge>
        <span className="font-mono">content_hash {graph.content_hash.slice(0, 12)}</span>
      </div>

      {nodes.length > 0 && (
        <div>
          <p className="mb-1.5 text-xs font-medium text-muted-foreground">节点</p>
          <div className="flex flex-wrap gap-1.5">
            {nodes.map((node) => (
              <NodePill key={node.id} node={node} />
            ))}
          </div>
        </div>
      )}

      {edges.length > 0 && (
        <div>
          <p className="mb-1.5 flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
            <GitCompare className="size-3.5" /> 边
          </p>
          <div className="space-y-1 rounded-lg border bg-muted/20 p-2">
            {edges.map((edge, i) => (
              <div key={`${edge.source}-${edge.target}-${i}`} className="flex flex-wrap items-center gap-1.5 font-mono text-xs">
                <span className="text-muted-foreground">{edge.source}</span>
                <span className="text-primary">→</span>
                <span className="text-muted-foreground">{edge.target}</span>
                {edge.relation && (
                  <Badge tone="info" className="font-mono">{edge.relation}</Badge>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {nodes.length === 0 && edges.length === 0 && (
        <p className="text-xs text-muted-foreground">图谱为空（无节点/边）。</p>
      )}
    </div>
  )
}
