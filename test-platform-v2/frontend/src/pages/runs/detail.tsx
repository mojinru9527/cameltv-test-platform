import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router'
import { getAiqeRun } from '@/api/aiqeRuns'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import type { AiqeRun, AiqeRunArtifact } from '@/types/aiqe'
import { useRunEvents } from './useRunEvents'

export default function RunDetailPage() {
  const { runId } = useParams<{ runId: string }>()
  useDocumentTitle('Run 详情')

  const [run, setRun] = useState<AiqeRun | null>(null)
  const [artifacts, setArtifacts] = useState<AiqeRunArtifact[]>([])
  const [error, setError] = useState('')
  const events = useRunEvents(runId)

  useEffect(() => {
    if (!runId) return
    let alive = true
    getAiqeRun(runId)
      .then((data) => {
        if (!alive) return
        setRun(data.run)
        setArtifacts(data.artifacts)
      })
      .catch((err: unknown) => {
        if (alive) setError(err instanceof Error ? err.message : '加载失败')
      })
    return () => {
      alive = false
    }
  }, [runId])

  return (
    <div className="space-y-6 p-6">
      <header className="space-y-1">
        <Link className="text-sm text-primary hover:underline" to="/runs">
          ← 返回执行中心
        </Link>
        <h1 className="font-mono text-2xl font-semibold">{run?.run_key ?? runId}</h1>
      </header>

      {error ? <p className="text-sm text-destructive">{error}</p> : null}

      {run ? (
        <dl className="grid grid-cols-2 gap-3 rounded-lg border p-4 text-sm md:grid-cols-4">
          <div>
            <dt className="text-muted-foreground">状态</dt>
            <dd className="font-medium">{run.status}</dd>
          </div>
          <div>
            <dt className="text-muted-foreground">结论</dt>
            <dd className="font-medium">{run.outcome ?? '—'}</dd>
          </div>
          <div>
            <dt className="text-muted-foreground">来源</dt>
            <dd className="font-medium">{run.source_type}</dd>
          </div>
          <div>
            <dt className="text-muted-foreground">耗时</dt>
            <dd className="font-medium">{run.duration_ms != null ? `${run.duration_ms} ms` : '—'}</dd>
          </div>
        </dl>
      ) : null}

      <section className="space-y-2">
        <h2 className="text-lg font-semibold">事件流（{events.length}）</h2>
        <ol className="space-y-1 rounded-lg border p-3 text-sm">
          {events.length === 0 ? (
            <li className="text-muted-foreground">暂无事件</li>
          ) : (
            events.map((event) => (
              <li key={event.id} className="flex gap-3 border-b py-1 last:border-b-0">
                <span className="w-10 shrink-0 font-mono text-muted-foreground">#{event.seq}</span>
                <span className="font-medium">{event.event_type}</span>
                <span className="text-muted-foreground">{event.producer}</span>
                <span className="ml-auto text-muted-foreground">
                  {new Date(event.occurred_at).toLocaleTimeString()}
                </span>
              </li>
            ))
          )}
        </ol>
      </section>

      <section className="space-y-2">
        <h2 className="text-lg font-semibold">Artifacts（{artifacts.length}）</h2>
        <div className="overflow-hidden rounded-lg border">
          <table className="w-full text-sm">
            <thead className="bg-muted/40 text-left">
              <tr>
                <th className="px-3 py-2">类型</th>
                <th className="px-3 py-2">大小</th>
                <th className="px-3 py-2">脱敏</th>
                <th className="px-3 py-2">sha256</th>
              </tr>
            </thead>
            <tbody>
              {artifacts.length === 0 ? (
                <tr>
                  <td className="px-3 py-6 text-center text-muted-foreground" colSpan={4}>
                    暂无 Artifact
                  </td>
                </tr>
              ) : (
                artifacts.map((artifact) => (
                  <tr key={artifact.id} className="border-t">
                    <td className="px-3 py-2">{artifact.artifact_type}</td>
                    <td className="px-3 py-2">{artifact.size_bytes} B</td>
                    <td className="px-3 py-2">{artifact.redaction_status}</td>
                    <td className="px-3 py-2 font-mono text-xs">{artifact.sha256.slice(0, 16)}…</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  )
}
