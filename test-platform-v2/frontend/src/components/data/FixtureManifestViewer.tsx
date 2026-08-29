import { Badge } from '@/ui'
import type { FixtureEntity } from '@/api/fixtures'

export interface FixtureManifestViewerProps {
  /** Raw `manifest_json` from the fixture detail. */
  manifest: Record<string, unknown> | null
  /** Structured `entities` array — the primary rendering source. */
  entities: FixtureEntity[]
}

/** Renders a fixture's manifest entities in a readable, non-SQL table. */
export function FixtureManifestViewer({ manifest, entities }: FixtureManifestViewerProps) {
  if (entities.length === 0) {
    if (!manifest || Object.keys(manifest).length === 0) {
      return (
        <p className="rounded-md border border-dashed px-3 py-3 text-center text-xs text-muted-foreground">
          暂无实体清单。
        </p>
      )
    }
    // Fall back to a summary of a manifest that is not an entities list.
    return (
      <div className="space-y-1">
        {Object.entries(manifest).map(([key, value]) => (
          <div key={key} className="grid grid-cols-[180px_1fr] gap-2 text-sm">
            <span className="font-mono text-xs text-muted-foreground">{key}</span>
            <code className="break-all rounded bg-muted/50 px-1.5 py-0.5 font-mono text-xs">
              {typeof value === 'string' ? value : JSON.stringify(value)}
            </code>
          </div>
        ))}
      </div>
    )
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm">
        <thead>
          <tr className="border-b text-xs text-muted-foreground">
            <th className="px-2 py-1.5 font-medium">实体</th>
            <th className="px-2 py-1.5 font-medium">类型</th>
            <th className="px-2 py-1.5 font-medium">快照</th>
            <th className="px-2 py-1.5 font-medium">行数</th>
            <th className="px-2 py-1.5 font-medium">哈希</th>
          </tr>
        </thead>
        <tbody>
          {entities.map((entity, i) => (
            <tr key={entity.entity_id ?? i} className="border-b last:border-0">
              <td className="px-2 py-1.5 font-mono text-xs">{entity.entity_id}</td>
              <td className="px-2 py-1.5">{entity.entity_type}</td>
              <td className="px-2 py-1.5">
                {entity.snapshot_type ? (
                  <Badge variant="outline">{entity.snapshot_type}</Badge>
                ) : (
                  <span className="text-xs text-muted-foreground">—</span>
                )}
              </td>
              <td className="px-2 py-1.5">{entity.row_count ?? '—'}</td>
              <td className="px-2 py-1.5 font-mono text-xs text-muted-foreground">
                {entity.content_hash ?? '—'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
