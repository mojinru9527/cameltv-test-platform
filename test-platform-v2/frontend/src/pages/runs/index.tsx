import { useEffect, useState } from 'react'
import { Link } from 'react-router'
import { listAiqeRuns } from '@/api/aiqeRuns'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import type { AiqeRun } from '@/types/aiqe'

export default function RunListPage() {
  useDocumentTitle('执行中心')
  const [runs, setRuns] = useState<AiqeRun[]>([])
  const [total, setTotal] = useState(0)
  const [error, setError] = useState('')

  useEffect(() => {
    let alive = true
    listAiqeRuns({ limit: 50 })
      .then((data) => {
        if (!alive) return
        setRuns(data.items)
        setTotal(data.total)
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
      <header className="flex items-baseline justify-between">
        <div>
          <h1 className="text-2xl font-semibold">执行中心</h1>
          <p className="text-sm text-muted-foreground">Run 列表（M1 Run Console）</p>
        </div>
        <span className="text-sm text-muted-foreground">共 {total} 条</span>
      </header>

      {error ? <p className="text-sm text-destructive">{error}</p> : null}

      <div className="overflow-hidden rounded-lg border">
        <table className="w-full text-sm">
          <thead className="bg-muted/40 text-left">
            <tr>
              <th className="px-3 py-2">Run</th>
              <th className="px-3 py-2">来源</th>
              <th className="px-3 py-2">状态</th>
              <th className="px-3 py-2">结论</th>
              <th className="px-3 py-2">创建时间</th>
            </tr>
          </thead>
          <tbody>
            {runs.length === 0 ? (
              <tr>
                <td className="px-3 py-6 text-center text-muted-foreground" colSpan={5}>
                  暂无 Run
                </td>
              </tr>
            ) : (
              runs.map((run) => (
                <tr key={run.id} className="border-t">
                  <td className="px-3 py-2">
                    <Link className="font-mono text-primary hover:underline" to={`/runs/${run.id}`}>
                      {run.run_key}
                    </Link>
                  </td>
                  <td className="px-3 py-2">{run.source_type}</td>
                  <td className="px-3 py-2">{run.status}</td>
                  <td className="px-3 py-2">{run.outcome ?? '—'}</td>
                  <td className="px-3 py-2">{new Date(run.created_at).toLocaleString()}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
