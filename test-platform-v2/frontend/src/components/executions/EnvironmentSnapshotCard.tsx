import type { EnvironmentSnapshot } from '@/api/executions'

export default function EnvironmentSnapshotCard({
  snapshot,
}: {
  snapshot?: EnvironmentSnapshot | null
}) {
  if (!snapshot) {
    return <p className="py-4 text-center text-sm text-muted-foreground">未采集环境快照。</p>
  }

  const fields: { label: string; value?: string | null }[] = [
    { label: '构建标签', value: snapshot.build_label },
    { label: '前端版本', value: snapshot.frontend_version },
    { label: 'DB Schema', value: snapshot.db_schema_version },
    { label: 'OpenAPI Hash', value: snapshot.openapi_hash },
    { label: '配置 Hash', value: snapshot.config_hash },
    { label: '静态资产 Hash', value: snapshot.static_asset_hash },
    { label: '体征指纹', value: snapshot.fingerprint_hash },
    { label: '采集时间', value: snapshot.captured_at },
    { label: '采集方式', value: snapshot.created_by_type },
  ]

  return (
    <dl className="space-y-1.5 text-sm">
      {fields.map((f) => (
        <div key={f.label} className="flex items-center justify-between gap-2">
          <dt className="shrink-0 text-muted-foreground">{f.label}</dt>
          <dd className="break-all font-mono text-xs">{f.value ?? '—'}</dd>
        </div>
      ))}
      {snapshot.service_versions_json && (
        <details className="rounded-lg border p-2">
          <summary className="cursor-pointer text-xs text-muted-foreground">服务版本</summary>
          <pre className="mt-2 max-h-48 overflow-auto rounded bg-muted p-2 text-xs">
            {JSON.stringify(snapshot.service_versions_json, null, 2)}
          </pre>
        </details>
      )}
      {snapshot.manual_note && (
        <div className="flex items-start justify-between gap-2">
          <dt className="shrink-0 text-muted-foreground">备注</dt>
          <dd className="text-xs">{snapshot.manual_note}</dd>
        </div>
      )}
    </dl>
  )
}
