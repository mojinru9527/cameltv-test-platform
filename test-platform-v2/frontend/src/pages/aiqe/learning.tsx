import { useEffect, useState } from 'react'
import { Badge, Button, Card, CardContent, CardHeader, CardTitle, Input } from '@/ui'
import {
  activateLearningCandidate,
  approveLearningCandidate,
  evaluateLearningCandidate,
  listLearningCandidates,
  type LearningCandidate,
} from '@/api/aiqeConsole'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import ConsoleTabs from './ConsoleTabs'

const STATUS_LABEL: Record<string, string> = {
  draft: '草稿',
  benchmarked: '待人工审批',
  approved: '已批准',
  active: '已激活',
}

function errorText(err: unknown): string {
  return err instanceof Error ? err.message : '请求失败'
}

export default function LearningCandidatesPage() {
  useDocumentTitle('学习候选')
  const [rows, setRows] = useState<LearningCandidate[]>([])
  const [error, setError] = useState('')
  const [busyId, setBusyId] = useState('')
  const [falsePositiveRate, setFalsePositiveRate] = useState('0.1')
  const [sampleSize, setSampleSize] = useState('50')

  useEffect(() => {
    let alive = true
    listLearningCandidates()
      .then((data) => {
        if (alive) setRows(data)
      })
      .catch((err: unknown) => {
        if (alive) setError(errorText(err))
      })
    return () => {
      alive = false
    }
  }, [])

  function replace(row: LearningCandidate) {
    setRows((prev) => prev.map((item) => (item.id === row.id ? row : item)))
  }

  async function run(id: string, action: () => Promise<LearningCandidate>) {
    setBusyId(id)
    setError('')
    try {
      replace(await action())
    } catch (err: unknown) {
      setError(errorText(err))
    } finally {
      setBusyId('')
    }
  }

  async function handleActivate(row: LearningCandidate) {
    setBusyId(row.id)
    setError('')
    try {
      const result = await activateLearningCandidate(row.id)
      replace(result.candidate)
    } catch (err: unknown) {
      setError(errorText(err))
    } finally {
      setBusyId('')
    }
  }

  return (
    <div className="space-y-4 p-6">
      <header className="space-y-3">
        <div>
          <h1 className="text-2xl font-semibold">学习候选</h1>
          <p className="text-sm text-muted-foreground">
            草稿 → 基准评估 → 人工批准 → 激活。批准需要 aiqe:learning:approve；误报率超过 20% 会被服务端拒绝。
          </p>
        </div>
        <ConsoleTabs />
      </header>

      {error ? <p className="text-sm text-destructive">{error}</p> : null}

      <Card>
        <CardHeader>
          <CardTitle className="text-base">基准评估参数</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-wrap items-end gap-3">
          <label className="space-y-1 text-sm">
            <span className="text-muted-foreground">误报率（0-1）</span>
            <Input
              className="w-32"
              onChange={(event) => setFalsePositiveRate(event.target.value)}
              value={falsePositiveRate}
            />
          </label>
          <label className="space-y-1 text-sm">
            <span className="text-muted-foreground">样本量</span>
            <Input
              className="w-32"
              onChange={(event) => setSampleSize(event.target.value)}
              value={sampleSize}
            />
          </label>
        </CardContent>
      </Card>

      <div className="overflow-hidden rounded-lg border">
        <table className="w-full text-sm">
          <thead className="bg-muted/40 text-left">
            <tr>
              <th className="px-3 py-2">Pattern</th>
              <th className="px-3 py-2">来源</th>
              <th className="px-3 py-2">状态</th>
              <th className="px-3 py-2">Benchmark</th>
              <th className="px-3 py-2">创建时间</th>
              <th className="px-3 py-2 text-right">操作</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr>
                <td className="px-3 py-6 text-center text-muted-foreground" colSpan={6}>
                  暂无学习候选
                </td>
              </tr>
            ) : (
              rows.map((row) => {
                const benchmark = row.benchmark
                const isBusy = busyId === row.id
                return (
                  <tr className="border-t" key={row.id}>
                    <td className="max-w-[28rem] px-3 py-2">
                      <div className="font-medium">{row.rule.pattern || row.id.slice(0, 8)}</div>
                      {row.rule.description ? (
                        <div className="text-xs text-muted-foreground">{row.rule.description}</div>
                      ) : null}
                    </td>
                    <td className="px-3 py-2">{row.source}</td>
                    <td className="px-3 py-2">
                      <Badge
                        tone={
                          row.status === 'active'
                            ? 'success'
                            : row.status === 'benchmarked'
                              ? 'warning'
                              : 'neutral'
                        }
                      >
                        {STATUS_LABEL[row.status] || row.status}
                      </Badge>
                    </td>
                    <td className="px-3 py-2 text-xs">
                      {benchmark
                        ? `FPR ${benchmark.false_positive_rate ?? '-'} / n=${benchmark.sample_size ?? '-'}`
                        : '-'}
                    </td>
                    <td className="px-3 py-2">{new Date(row.created_at).toLocaleString()}</td>
                    <td className="space-x-2 px-3 py-2 text-right">
                      {row.status === 'draft' ? (
                        <Button
                          disabled={isBusy}
                          onClick={() =>
                            void run(row.id, () =>
                              evaluateLearningCandidate(row.id, {
                                false_positive_rate: Number(falsePositiveRate),
                                sample_size: Number(sampleSize),
                              }),
                            )
                          }
                          size="sm"
                          variant="outline"
                        >
                          基准评估
                        </Button>
                      ) : null}
                      {row.status === 'benchmarked' ? (
                        <Button
                          disabled={isBusy}
                          onClick={() =>
                            void run(row.id, () => approveLearningCandidate(row.id))
                          }
                          size="sm"
                        >
                          人工批准
                        </Button>
                      ) : null}
                      {row.status === 'approved' ? (
                        <Button
                          disabled={isBusy}
                          onClick={() => void handleActivate(row)}
                          size="sm"
                          variant="outline"
                        >
                          激活
                        </Button>
                      ) : null}
                      {row.status === 'active' ? (
                        <span className="text-xs text-muted-foreground">已生效</span>
                      ) : null}
                    </td>
                  </tr>
                )
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
