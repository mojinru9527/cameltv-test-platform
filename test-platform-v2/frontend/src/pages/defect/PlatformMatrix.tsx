import { Badge, Card, CardContent } from '@/ui'

export interface PlatformBinding {
  platform: string
  build: string
  device: string
  profile: string
  actual: string
  evidence: string[]
}

export interface AcPlatformRow {
  ac_id: string
  ac_text: string
  semantic_type?: string
  bindings: PlatformBinding[]
}

const PLATFORM_LABEL: Record<string, string> = {
  web: 'Web',
  h5: 'H5',
  miniapp: '小程序',
  android: 'Android',
  ios: 'iOS',
}

export default function PlatformMatrix({ rows }: { rows: AcPlatformRow[] }) {
  const platforms = Array.from(new Set(rows.flatMap((row) => row.bindings.map((item) => item.platform))))

  if (rows.length === 0 || platforms.length === 0) {
    return (
      <Card size="sm">
        <CardContent>
          <p className="text-sm text-muted-foreground">暂无平台验收数据</p>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card size="sm">
      <CardContent className="overflow-x-auto p-0">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b text-left text-muted-foreground">
              <th className="p-3 font-medium">验收标准</th>
              <th className="p-3 font-medium">语义类型</th>
              {platforms.map((platform) => (
                <th key={platform} className="p-3 font-medium">
                  {PLATFORM_LABEL[platform] ?? platform}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.ac_id} className="border-b align-top last:border-0">
                <td className="p-3">
                  <div className="font-medium">{row.ac_id}</div>
                  <div className="text-muted-foreground">{row.ac_text}</div>
                </td>
                <td className="p-3">
                  {row.semantic_type ? (
                    <Badge tone="info">{row.semantic_type}</Badge>
                  ) : (
                    <span className="text-muted-foreground">—</span>
                  )}
                </td>
                {platforms.map((platform) => {
                  const binding = row.bindings.find((item) => item.platform === platform)
                  if (!binding) {
                    return (
                      <td key={platform} className="p-3 text-muted-foreground">
                        —
                      </td>
                    )
                  }
                  return (
                    <td key={platform} className="p-3 space-y-1">
                      <div>{binding.actual}</div>
                      <div className="text-xs text-muted-foreground font-mono">
                        {binding.build} · {binding.device} · {binding.profile}
                      </div>
                      <div className="flex flex-wrap gap-1">
                        {binding.evidence.map((ref) => (
                          <code key={ref} className="text-xs bg-muted rounded px-1.5 py-0.5">
                            {ref}
                          </code>
                        ))}
                      </div>
                    </td>
                  )
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </CardContent>
    </Card>
  )
}
