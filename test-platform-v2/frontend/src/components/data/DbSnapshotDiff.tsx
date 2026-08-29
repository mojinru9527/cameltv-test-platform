import { Badge } from '@/ui'
import { GitCompare, Plus, MinusCircle, Pencil } from '@/lib/icons'
import type { FixtureSnapshot } from '@/api/fixtures'

export interface DbSnapshotDiffProps {
  snapshots: FixtureSnapshot[]
}

interface DiffPair {
  entityId: string
  snapshotType: string
  before: FixtureSnapshot
  after: FixtureSnapshot
  added: string[]
  removed: string[]
  changed: string[]
  identical: boolean
}

function topLevelKeys(value: Record<string, unknown> | null): Record<string, unknown> {
  return value ?? {}
}

function diffKeys(beforeValue: Record<string, unknown> | null, afterValue: Record<string, unknown> | null): {
  added: string[]
  removed: string[]
  changed: string[]
  identical: boolean
} {
  const before = topLevelKeys(beforeValue)
  const after = topLevelKeys(afterValue)
  const beforeKeys = new Set(Object.keys(before))
  const afterKeys = new Set(Object.keys(after))
  const added = [...afterKeys].filter((k) => !beforeKeys.has(k))
  const removed = [...beforeKeys].filter((k) => !afterKeys.has(k))
  const changed = [...beforeKeys]
    .filter((k) => afterKeys.has(k))
    .filter((k) => JSON.stringify(before[k]) !== JSON.stringify(after[k]))
  const identical = added.length === 0 && removed.length === 0 && changed.length === 0
  return { added, removed, changed, identical }
}

/**
 * Compares before/after fixtures snapshots paired by entity + snapshot_type and
 * reports which top-level keys were added / removed / changed. This is a
 * business-level diff — it never renders SQL.
 */
export function DbSnapshotDiff({ snapshots }: DbSnapshotDiffProps) {
  const groups = new Map<string, FixtureSnapshot[]>()
  for (const s of snapshots) {
    const key = `${s.entity_id ?? 'global'}|${s.snapshot_type}`
    const list = groups.get(key) ?? []
    list.push(s)
    groups.set(key, list)
  }

  const pairs: DiffPair[] = []
  for (const list of groups.values()) {
    const ordered = [...list].sort((a, b) => {
      const aTime = a.created_at ? new Date(a.created_at).getTime() : a.id
      const bTime = b.created_at ? new Date(b.created_at).getTime() : b.id
      return aTime - bTime
    })
    if (ordered.length >= 2) {
      const before = ordered[0]
      const after = ordered[ordered.length - 1]
      const { added, removed, changed, identical } = diffKeys(before.snapshot_json, after.snapshot_json)
      pairs.push({
        entityId: String(after.entity_id ?? before.entity_id ?? 'global'),
        snapshotType: after.snapshot_type ?? before.snapshot_type,
        before,
        after,
        added,
        removed,
        changed,
        identical,
      })
    }
  }

  if (pairs.length === 0) {
    return (
      <p className="rounded-md border border-dashed px-3 py-3 text-center text-xs text-muted-foreground">
        暂无可对比的快照（同一实体需至少存在前后两份快照）。
      </p>
    )
  }

  return (
    <div className="space-y-2">
      {pairs.map((pair) => (
        <div key={`${pair.entityId}|${pair.snapshotType}`} className="rounded-md border px-3 py-2">
          <div className="flex flex-wrap items-center gap-2">
            <GitCompare className="size-4 text-muted-foreground" />
            <span className="font-mono text-xs">{pair.entityId}</span>
            <Badge variant="outline">{pair.snapshotType}</Badge>
            {pair.identical ? (
              <Badge tone="neutral">无差异</Badge>
            ) : (
              <Badge tone="warning">有差异</Badge>
            )}
          </div>
          {pair.changed.length > 0 && (
            <div className="mt-1 flex flex-wrap gap-1">
              {pair.changed.map((k) => (
                <span key={k} className="inline-flex items-center gap-1 rounded bg-status-warning-muted px-1.5 py-0.5 text-xs">
                  <Pencil className="size-3" /> {k}
                </span>
              ))}
            </div>
          )}
          {pair.added.length > 0 && (
            <div className="mt-1 flex flex-wrap gap-1">
              {pair.added.map((k) => (
                <span key={k} className="inline-flex items-center gap-1 rounded bg-status-success-muted px-1.5 py-0.5 text-xs">
                  <Plus className="size-3" /> {k}
                </span>
              ))}
            </div>
          )}
          {pair.removed.length > 0 && (
            <div className="mt-1 flex flex-wrap gap-1">
              {pair.removed.map((k) => (
                <span key={k} className="inline-flex items-center gap-1 rounded bg-status-danger-muted px-1.5 py-0.5 text-xs">
                  <MinusCircle className="size-3" /> {k}
                </span>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  )
}
