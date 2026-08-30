import { useState } from 'react'
import { Badge, Button, Card, CardContent, CardHeader, CardTitle, Input, Label, Skeleton } from '@/ui'
import { toast } from 'sonner'
import PageHeader from '@/components/PageHeader'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import useAbortableEffect from '@/hooks/useAbortableEffect'
import {
  createModelEvaluation,
  listModelEvaluations,
  modelEvalRegressionCheck,
  type ModelEvaluation,
} from '@/api/aiClosedLoop'

/** V38-013 AI Model Evaluation admin: golden suite model/prompt comparison + regression gate. */
export default function AiEvaluationsPage() {
  useDocumentTitle('AI 模型评估')
  const [runs, setRuns] = useState<ModelEvaluation[]>([])
  const [loading, setLoading] = useState(false)
  const [suite, setSuite] = useState('')
  const [modelRef, setModelRef] = useState('')
  const [accuracy, setAccuracy] = useState('')
  const [regression, setRegression] = useState<{ passed: boolean; score: number; threshold: number; reason: string } | null>(null)

  useAbortableEffect((signal) => {
    setLoading(true)
    listModelEvaluations(signal)
      .then((rows) => setRuns(rows))
      .catch(() => undefined)
      .finally(() => {
        if (!signal?.aborted) setLoading(false)
      })
  }, [])

  const createRun = async () => {
    if (!suite.trim() || !modelRef.trim()) {
      toast.error('请输入 evaluation_suite 与 model_ref')
      return
    }
    try {
      await createModelEvaluation({
        evaluation_suite: suite.trim(),
        model_ref: modelRef.trim(),
        metrics: { accuracy: Number(accuracy) || 0, n: 0 },
        status: 'COMPLETED',
      })
      toast.success('评估已记录')
      setSuite('')
      setModelRef('')
      setAccuracy('')
      const rows = await listModelEvaluations()
      setRuns(rows)
    } catch (err) {
      toast.error((err as Error).message || '记录失败')
    }
  }

  const checkRegression = async () => {
    if (!suite.trim()) {
      toast.error('请输入 evaluation_suite')
      return
    }
    try {
      const res = await modelEvalRegressionCheck(suite.trim())
      setRegression(res)
    } catch (err) {
      toast.error((err as Error).message || '回归检查失败')
    }
  }

  return (
    <div className="space-y-4">
      <PageHeader title="AI 模型评估" description="Golden Suite 模型/Prompt 比较 + 回归门禁（V38-013）" />

      <Card>
        <CardHeader>
          <CardTitle>记录一次离线评估</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="grid gap-3 sm:grid-cols-3">
            <div className="space-y-1.5">
              <Label>evaluation_suite</Label>
              <Input value={suite} onChange={(e) => setSuite(e.target.value)} placeholder="如 failure-triage-golden" />
            </div>
            <div className="space-y-1.5">
              <Label>model_ref</Label>
              <Input value={modelRef} onChange={(e) => setModelRef(e.target.value)} placeholder="模型引用" />
            </div>
            <div className="space-y-1.5">
              <Label>accuracy</Label>
              <Input value={accuracy} onChange={(e) => setAccuracy(e.target.value)} placeholder="0.95" />
            </div>
          </div>
          <div className="flex gap-2">
            <Button onClick={createRun}>记录</Button>
            <Button variant="secondary" onClick={checkRegression}>回归检查</Button>
          </div>
        </CardContent>
      </Card>

      {regression && (
        <div className={`rounded-md border p-3 text-sm ${regression.passed ? 'border-status-success text-status-success' : 'border-status-danger text-status-danger'}`}>
          {regression.passed ? 'Golden 阈值通过。' : 'Golden 阈值未达，阻止发布。'} 得分 {regression.score.toFixed(2)} / 阈值 {regression.threshold}
        </div>
      )}

      {loading ? (
        <Skeleton className="h-40 w-full" />
      ) : runs.length === 0 ? (
        <div className="rounded-md border border-dashed px-3 py-10 text-center text-sm text-muted-foreground">
          暂无评估记录
        </div>
      ) : (
        <div className="space-y-2">
          {runs.map((r) => (
            <div key={r.id} className="rounded-md border p-3">
              <div className="flex flex-wrap items-center gap-2">
                <Badge tone="neutral">{r.evaluation_suite}</Badge>
                <Badge tone="neutral">{r.model_ref}</Badge>
                <span className="text-xs text-muted-foreground">#{r.id} · {r.status}</span>
                <span className="ml-auto text-xs text-muted-foreground">accuracy {(Number(r.metrics?.accuracy) || 0).toFixed(2)}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
