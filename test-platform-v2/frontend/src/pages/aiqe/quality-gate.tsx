import { useState, type FormEvent } from 'react'
import { Badge, Button, Card, CardContent, CardHeader, CardTitle, Input } from '@/ui'
import { evaluateQualityGate, type QualityGateResult } from '@/api/aiqeConsole'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import ConsoleTabs from './ConsoleTabs'

const TONE = {
  PASS: 'success',
  FAIL: 'danger',
  BLOCKED: 'warning',
} as const

export default function QualityGatePage() {
  useDocumentTitle('质量门禁')
  const [runIds, setRunIds] = useState('')
  const [versionTaskId, setVersionTaskId] = useState('')
  const [buildRef, setBuildRef] = useState('')
  const [environmentRef, setEnvironmentRef] = useState('')
  const [result, setResult] = useState<QualityGateResult | null>(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (busy) return
    const ids = runIds
      .split(',')
      .map((item) => item.trim())
      .filter(Boolean)
    const taskId = versionTaskId.trim() ? Number(versionTaskId) : undefined
    if (ids.length === 0 && !taskId) {
      setError('必须提供 Run IDs 或 VersionTask ID（门禁只从服务端事实计算）')
      return
    }
    setBusy(true)
    setError('')
    try {
      setResult(
        await evaluateQualityGate({
          run_ids: ids,
          version_task_id: taskId,
          build_ref: buildRef.trim(),
          environment_ref: environmentRef.trim(),
        }),
      )
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : '判定失败')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="space-y-4 p-6">
      <header className="space-y-3">
        <div>
          <h1 className="text-2xl font-semibold">质量门禁</h1>
          <p className="text-sm text-muted-foreground">
            只接受 Run / VersionTask 事实定位参数；服务端从 P0 断言计算并保存不可变快照。
            未知/未执行/失败一律不得 PASS。
          </p>
        </div>
        <ConsoleTabs />
      </header>

      {error ? <p className="text-sm text-destructive">{error}</p> : null}

      <Card>
        <CardHeader>
          <CardTitle className="text-base">判定输入</CardTitle>
        </CardHeader>
        <CardContent>
          <form className="space-y-4" onSubmit={handleSubmit}>
            <div className="grid gap-3 md:grid-cols-2">
              <label className="space-y-1 text-sm">
                <span className="text-muted-foreground">Run IDs（逗号分隔）</span>
                <Input
                  aria-label="Run IDs"
                  onChange={(event) => setRunIds(event.target.value)}
                  placeholder="run-uuid-1, run-uuid-2"
                  value={runIds}
                />
              </label>
              <label className="space-y-1 text-sm">
                <span className="text-muted-foreground">VersionTask ID（可选）</span>
                <Input
                  aria-label="VersionTask ID"
                  min={1}
                  onChange={(event) => setVersionTaskId(event.target.value)}
                  type="number"
                  value={versionTaskId}
                />
              </label>
              <label className="space-y-1 text-sm">
                <span className="text-muted-foreground">Build（可选）</span>
                <Input
                  aria-label="Build"
                  onChange={(event) => setBuildRef(event.target.value)}
                  value={buildRef}
                />
              </label>
              <label className="space-y-1 text-sm">
                <span className="text-muted-foreground">Environment ID（可选）</span>
                <Input
                  aria-label="Environment ID"
                  onChange={(event) => setEnvironmentRef(event.target.value)}
                  value={environmentRef}
                />
              </label>
            </div>
            <Button disabled={busy} type="submit">
              {busy ? '判定中…' : '判定门禁'}
            </Button>
          </form>
        </CardContent>
      </Card>

      {result ? (
        <Card data-testid="quality-gate-result">
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="text-base">判定结果</CardTitle>
            <Badge tone={TONE[result.gate_status]}>{result.gate_status}</Badge>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <p className="text-muted-foreground">
              P0 {result.p0_passed}/{result.p0_total} 通过 · 失败 {result.p0_failed} · 阻断{' '}
              {result.p0_blocked} · 事实 Run {result.source_ids.length} 条 · 规则{' '}
              {result.rule_version}
            </p>
            {result.reasons.length > 0 ? (
              <ul className="list-disc space-y-1 pl-5 text-destructive">
                {result.reasons.map((reason) => (
                  <li key={reason}>{reason}</li>
                ))}
              </ul>
            ) : (
              <p className="text-status-success">P0 全部通过</p>
            )}
          </CardContent>
        </Card>
      ) : null}
    </div>
  )
}
