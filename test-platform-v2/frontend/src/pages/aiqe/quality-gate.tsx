import { useState, type FormEvent } from 'react'
import { Badge, Button, Card, CardContent, CardHeader, CardTitle, Input } from '@/ui'
import { evaluateQualityGate, type QualityGateResult } from '@/api/aiqeConsole'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import ConsoleTabs from './ConsoleTabs'

const FIELDS = [
  { key: 'p0_total', label: 'P0 总数' },
  { key: 'p0_passed', label: 'P0 通过' },
  { key: 'p0_failed', label: 'P0 失败' },
  { key: 'p0_unknown', label: 'P0 未知' },
  { key: 'p0_not_run', label: 'P0 未执行' },
] as const

type CountKey = (typeof FIELDS)[number]['key']
type Counts = Record<CountKey, number>

const INITIAL: Counts = {
  p0_total: 0,
  p0_passed: 0,
  p0_failed: 0,
  p0_unknown: 0,
  p0_not_run: 0,
}

const TONE = {
  PASS: 'success',
  FAIL: 'danger',
  BLOCKED: 'warning',
} as const

export default function QualityGatePage() {
  useDocumentTitle('质量门禁')
  const [counts, setCounts] = useState<Counts>(INITIAL)
  const [result, setResult] = useState<QualityGateResult | null>(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (busy) return
    setBusy(true)
    setError('')
    try {
      setResult(await evaluateQualityGate(counts))
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
            只有 P0 全部通过才显示 PASS；未知/未执行/失败一律不得 PASS。
          </p>
        </div>
        <ConsoleTabs />
      </header>

      {error ? <p className="text-sm text-destructive">{error}</p> : null}

      <Card>
        <CardHeader>
          <CardTitle className="text-base">P0 统计</CardTitle>
        </CardHeader>
        <CardContent>
          <form className="space-y-4" onSubmit={handleSubmit}>
            <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
              {FIELDS.map((field) => (
                <label className="space-y-1 text-sm" key={field.key}>
                  <span className="text-muted-foreground">{field.label}</span>
                  <Input
                    aria-label={field.label}
                    min={0}
                    onChange={(event) =>
                      setCounts((prev) => ({
                        ...prev,
                        [field.key]: Math.max(0, Number(event.target.value) || 0),
                      }))
                    }
                    type="number"
                    value={counts[field.key]}
                  />
                </label>
              ))}
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
              P0 {result.p0_passed}/{result.p0_total} 通过 · 失败 {result.p0_failed} · 未知{' '}
              {result.p0_unknown} · 未执行 {result.p0_not_run}
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
