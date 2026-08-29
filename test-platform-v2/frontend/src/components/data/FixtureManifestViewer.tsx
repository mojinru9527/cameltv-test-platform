import { Badge } from '@/ui'
import type { FixtureEntity } from '@/api/fixtures'

export interface FixtureManifestViewerProps {
  /** Raw `manifest_json` (parsed). Backend emits an array of entity specs or an object. */
  manifest: unknown
  /** Structured `entities` array — the primary rendering source. */
  entities: FixtureEntity[]
}

/** Renders a fixture's manifest entities in a readable, non-SQL table. */
export function FixtureManifestViewer({ manifest, entities }: FixtureManifestViewerProps) {
  if (entities.length === 0) {
    const entries = Array.isArray(manifest)
      ? manifest.map((e, i) => [`entity[${i}]`, e] as const)
      : Object.entries((manifest ?? {}) as Record<string, unknown>)
    if (entries.length === 0) {
      return (
        <p className="rounded-md border border-dashed px-3 py-3 text-center text-xs text-muted-foreground">
          暂无实体清单。
        </p>
      )
    }
    return (
      <div className="space-y-1">
        {entries.map(([key, value]) => (
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
            <th className="px-2 py-1.5 font-medium">实体类型</th>
            <th className="px-2 py-1.5 font-medium">逻辑键</th>
            <th className="px-2 py-1.5 font-medium">物理引用</th>
            <th className="px-2 py-1.5 font-medium">由来</th>
            <th className="px-2 py-1.5 font-medium">清理动作</th>
          </tr>
        </thead>
        <tbody>
          {entities.map((entity) => (
            <tr key={entity.id} className="border-b last:border-0">
              <td className="px-2 py-1.5 font-mono text-xs">{entity.entity_type}</td>
              <td className="px-2 py-1.5 font-mono text-xs">{entity.logical_key}</td>
              <td className="px-2 py-1.5">
                <code className="break-all rounded bg-muted/50 px-1.5 py-0.5 font-mono text-xs">
                  {entity.physical_ref_json ? JSON.stringify(entity.physical_ref_json) : '—'}
                </code>
              </td>
              <td className="px-2 py-1.5">
                {entity.created_by_fixture ? (
                  <Badge variant="outline">夹具创建</Badge>
                ) : (
                  <Badge tone="neutral">已有</Badge>
                )}
              </td>
              <td className="px-2 py-1.5 text-xs">
                {entity.cleanup_action_json ? JSON.stringify(entity.cleanup_action_json) : '—'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
