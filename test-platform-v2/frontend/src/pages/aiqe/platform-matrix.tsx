import { useEffect, useState } from 'react'
import { Badge, Card, CardContent, CardHeader, CardTitle } from '@/ui'
import { getPlatformMatrix, type PlatformMatrix } from '@/api/aiqeConsole'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import ConsoleTabs from './ConsoleTabs'

export default function PlatformMatrixPage() {
  useDocumentTitle('平台矩阵')
  const [matrix, setMatrix] = useState<PlatformMatrix | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    let alive = true
    getPlatformMatrix()
      .then((data) => {
        if (alive) setMatrix(data)
      })
      .catch((err: unknown) => {
        if (alive) setError(err instanceof Error ? err.message : '加载失败')
      })
    return () => {
      alive = false
    }
  }, [])

  return (
    <div className="space-y-4 p-6">
      <header className="space-y-3">
        <div>
          <h1 className="text-2xl font-semibold">平台矩阵</h1>
          <p className="text-sm text-muted-foreground">
            节点自描述能力 × 平台；只有带实测 evidence 的节点计为可用。
          </p>
        </div>
        <ConsoleTabs />
      </header>

      {error ? <p className="text-sm text-destructive">{error}</p> : null}

      {matrix ? (
        <>
          <div className="flex flex-wrap items-center gap-2 text-sm">
            <Badge tone="info">平台 {matrix.platforms.length}</Badge>
            <Badge tone="info">能力 {matrix.capabilities.length}</Badge>
            <Badge tone={matrix.available_nodes > 0 ? 'success' : 'warning'}>
              可用节点 {matrix.available_nodes}/{matrix.nodes.length}
            </Badge>
          </div>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">能力覆盖矩阵</CardTitle>
            </CardHeader>
            <CardContent className="overflow-x-auto p-0">
              {matrix.rows.length === 0 ? (
                <p className="p-4 text-sm text-muted-foreground">暂无节点能力数据</p>
              ) : (
                <table className="w-full text-sm">
                  <thead className="bg-muted/40 text-left">
                    <tr>
                      <th className="px-3 py-2">能力</th>
                      {matrix.platforms.map((platform) => (
                        <th className="px-3 py-2" key={platform}>
                          {platform}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {matrix.rows.map((row) => (
                      <tr className="border-t" key={row.capability}>
                        <td className="px-3 py-2 font-mono text-xs">{row.capability}</td>
                        {matrix.platforms.map((platform) => {
                          const cell = row.cells[platform]
                          return (
                            <td className="px-3 py-2" key={platform}>
                              {cell?.available ? (
                                <span className="text-status-success" title={cell.nodes.join(', ')}>
                                  ✓ {cell.node_count}
                                </span>
                              ) : (
                                <span className="text-muted-foreground">—</span>
                              )}
                            </td>
                          )
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </CardContent>
          </Card>
        </>
      ) : !error ? (
        <p className="text-sm text-muted-foreground">加载中…</p>
      ) : null}
    </div>
  )
}
