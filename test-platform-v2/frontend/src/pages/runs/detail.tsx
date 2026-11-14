import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router'
import { getAiqeRun, listRunNodes } from '@/api/aiqeRuns'
import { Badge } from '@/ui'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import type { AiqeRun, AiqeRunArtifact, AiqeRunNode } from '@/types/aiqe'
import ConsoleTabs from '@/pages/aiqe/ConsoleTabs'
import { useRunEvents } from './useRunEvents'

function toneForStatus(status: string): 'success' | 'danger' | 'warning' | 'info' | 'neutral' {
  const normalized = status.toUpperCase()
  if (normalized === 'PASSED' || normalized === 'PASS' || normalized === 'COMPLETED') return 'success'
  if (normalized === 'FAILED' || normalized === 'FAIL' || normalized === 'ERROR') return 'danger'
  if (normalized === 'BLOCKED' || normalized === 'NOT_EVALUATED') return 'warning'
  if (normalized === 'RUNNING' || normalized === 'READY') return 'info'
  return 'neutral'
}

function preview(value: unknown): string {
  if (value == null) return '—'
  try {
    const text = JSON.stringify(value)
    return text.length > 400 ? `${text.slice(0, 400)}…` : text
  } catch {
    return String(value)
  }
}

export default function RunDetailPage() {
  const { runId } = useParams<{ runId: string }>()
  useDocumentTitle('Run 详情')

  const [run, setRun] = useState<AiqeRun | null>(null)
  const [artifacts, setArtifacts] = useState<AiqeRunArtifact[]>([])
  const [nodes, setNodes] = useState<AiqeRunNode[]>([])
  const [error, setError] = useState('')
  const { events, connection } = useRunEvents(runId)

  useEffect(() => {
    if (!runId) return
    let alive = true
    Promise.all([getAiqeRun(runId), listRunNodes(runId)])
      .then(([data, nodeData]) => {
        if (!alive) return
        setRun(data.run)
        setArtifacts(data.artifacts)
        setNodes(nodeData.nodes)
      })
      .catch((err: unknown) => {
        if (alive) setError(err instanceof Error ? err.message : '加载失败')
      })
    return () => {
      alive = false
    }
  }, [runId])

  useEffect(() => {
    if (!runId || events.length === 0) return
    const last = events[events.length - 1]
    if (last.event_type !== 'node.completed' && last.event_type !== 'run.completed') return
    let alive = true
    listRunNodes(runId)
      .then((data) => {
        if (alive) setNodes(data.nodes)
      })
      .catch(() => {})
    return () => {
      alive = false
    }
  }, [events, runId])

  return (
    <div className="space-y-6 p-6">
      <header className="space-y-3">
        <Link className="text-sm text-primary hover:underline" to="/runs">
          ← 返回执行中心
        </Link>
        <h1 className="font-mono text-2xl font-semibold">{run?.run_key ?? runId}</h1>
        <div className="flex items-center gap-2 text-sm">
          <span className="text-muted-foreground">事件通道：</span>
          {connection === 'live' ? (
            <Badge tone="success">实时</Badge>
          ) : connection === 'polling' ? (
            <Badge tone="warning">轮询中</Badge>
          ) : (
            <Badge tone="neutral">{connection === 'connecting' ? '连接中' : '未连接'}</Badge>
          )}
        </div>
        <ConsoleTabs />
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
        <h2 className="text-lg font-semibold">执行步骤（{nodes.length}）</h2>
        <div className="space-y-3">
          {nodes.length === 0 ? (
            <p className="rounded-lg border p-3 text-sm text-muted-foreground">暂无节点</p>
          ) : (
            nodes.map((item) => (
              <article key={item.node.id} className="space-y-3 rounded-lg border p-4">
                <header className="flex flex-wrap items-center gap-2">
                  <span className="font-mono text-sm font-semibold">{item.node.node_key}</span>
                  <Badge tone="neutral">{item.node.driver_key || '—'}</Badge>
                  <Badge tone={toneForStatus(item.node.status)}>{item.node.status}</Badge>
                  {item.node.error_class ? (
                    <span className="text-xs text-destructive">{item.node.error_class}</span>
                  ) : null}
                  <span className="ml-auto text-xs text-muted-foreground">
                    attempts {item.node.attempt_count} · artifacts {item.artifacts.length}
                  </span>
                </header>

                <div className="grid gap-2 md:grid-cols-2">
                  <details className="rounded border p-2 text-xs">
                    <summary className="cursor-pointer font-medium">输入（脱敏）</summary>
                    <pre className="mt-2 max-h-40 overflow-auto whitespace-pre-wrap break-all">
                      {preview(item.node.inputs)}
                    </pre>
                  </details>
                  <details className="rounded border p-2 text-xs">
                    <summary className="cursor-pointer font-medium">输出</summary>
                    <pre className="mt-2 max-h-40 overflow-auto whitespace-pre-wrap break-all">
                      {preview(item.node.outputs)}
                    </pre>
                  </details>
                </div>

                {item.attempts.length === 0 ? (
                  <p className="text-xs text-muted-foreground">暂无 Attempt</p>
                ) : (
                  item.attempts.map((attempt) => (
                    <div key={attempt.id} className="space-y-2 rounded border p-3">
                      <div className="flex items-center gap-2 text-xs">
                        <span className="font-mono">attempt #{attempt.attempt_no}</span>
                        <Badge tone={toneForStatus(attempt.status)}>{attempt.status}</Badge>
                        {attempt.error ? (
                          <span className="text-destructive">{preview(attempt.error)}</span>
                        ) : null}
                      </div>
                      <div className="overflow-hidden rounded border">
                        <table className="w-full text-xs">
                          <thead className="bg-muted/40 text-left">
                            <tr>
                              <th className="px-2 py-1">断言</th>
                              <th className="px-2 py-1">Oracle</th>
                              <th className="px-2 py-1">期望</th>
                              <th className="px-2 py-1">实际</th>
                              <th className="px-2 py-1">结论</th>
                            </tr>
                          </thead>
                          <tbody>
                            {attempt.assertions.length === 0 ? (
                              <tr>
                                <td className="px-2 py-2 text-muted-foreground" colSpan={5}>
                                  本 attempt 没有断言结果
                                </td>
                              </tr>
                            ) : (
                              attempt.assertions.map((assertion) => (
                                <tr key={assertion.id} className="border-t align-top">
                                  <td className="px-2 py-1 font-mono">{assertion.assertion_key}</td>
                                  <td className="px-2 py-1">
                                    {assertion.oracle_layer}:{assertion.oracle_ref || '—'}
                                  </td>
                                  <td className="max-w-40 truncate px-2 py-1" title={preview(assertion.expected)}>
                                    {preview(assertion.expected)}
                                  </td>
                                  <td className="max-w-40 truncate px-2 py-1" title={preview(assertion.actual)}>
                                    {preview(assertion.actual)}
                                  </td>
                                  <td className="px-2 py-1">
                                    <Badge tone={toneForStatus(assertion.status)}>{assertion.status}</Badge>
                                    {assertion.error ? (
                                      <div className="mt-1 text-destructive">{assertion.error}</div>
                                    ) : null}
                                  </td>
                                </tr>
                              ))
                            )}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  ))
                )}
              </article>
            ))
          )}
        </div>
      </section>

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
