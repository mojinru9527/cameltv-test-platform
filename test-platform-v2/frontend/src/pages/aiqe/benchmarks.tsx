import { useCallback, useState } from 'react'
import { Badge } from '@/ui'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import {
  addBenchmarkSample,
  createBenchmarkDataset,
  freezeBenchmarkDataset,
  getBenchmarkRun,
  runLlmBenchmark,
  type BenchmarkRunView,
} from '@/api/aiqeInsights'
import ConsoleTabs from './ConsoleTabs'

export default function BenchmarksPage() {
  useDocumentTitle('Benchmark')
  const [datasetKey, setDatasetKey] = useState('')
  const [taskType, setTaskType] = useState('learning')
  const [datasetId, setDatasetId] = useState('')
  const [sample, setSample] = useState({ sample_id: '', labels: 'A', labeler: '' })
  const [frozen, setFrozen] = useState<{
    sample_count: number
    content_hash: string
    gate_eligible: boolean
  } | null>(null)
  const [runId, setRunId] = useState('')
  const [run, setRun] = useState<BenchmarkRunView | null>(null)
  const [running, setRunning] = useState(false)
  const [error, setError] = useState('')

  const createDataset = useCallback(async () => {
    setError('')
    try {
      const created = await createBenchmarkDataset({ dataset_key: datasetKey, task_type: taskType })
      setDatasetId(created.id)
      setFrozen(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : '创建数据集失败')
    }
  }, [datasetKey, taskType])

  const addSample = useCallback(async () => {
    if (!datasetId) return
    setError('')
    try {
      await addBenchmarkSample(datasetId, {
        sample_id: sample.sample_id,
        golden_labels: sample.labels.split(',').map((item) => item.trim()).filter(Boolean),
        labeler: sample.labeler,
        reviewer: 'lead',
      })
      setSample({ sample_id: '', labels: 'A', labeler: sample.labeler })
    } catch (err) {
      setError(err instanceof Error ? err.message : '追加样本失败')
    }
  }, [datasetId, sample])

  const freeze = useCallback(async () => {
    if (!datasetId) return
    setError('')
    try {
      setFrozen(await freezeBenchmarkDataset(datasetId))
    } catch (err) {
      setError(err instanceof Error ? err.message : '冻结失败')
    }
  }, [datasetId])

  const execute = useCallback(async () => {
    if (!datasetId) return
    setError('')
    setRunning(true)
    try {
      setRun(await runLlmBenchmark(datasetId))
    } catch (err) {
      setError(err instanceof Error ? err.message : '运行 Benchmark 失败')
    } finally {
      setRunning(false)
    }
  }, [datasetId])

  const loadRun = useCallback(async () => {
    setError('')
    try {
      setRun(await getBenchmarkRun(runId.trim()))
    } catch (err) {
      setError(err instanceof Error ? err.message : '读取 BenchmarkRun 失败')
    }
  }, [runId])

  return (
    <div className="space-y-6 p-6">
      <header className="space-y-3">
        <h1 className="text-2xl font-semibold">Agent Benchmark（AUD-018）</h1>
        <ConsoleTabs />
      </header>

      {error ? <p className="text-sm text-destructive">{error}</p> : null}

      <section className="grid gap-4 lg:grid-cols-2">
        <div className="space-y-2 rounded-lg border p-4 text-sm">
          <h2 className="font-medium">1. 数据集</h2>
          <input
            className="w-full rounded border px-2 py-1"
            placeholder="dataset_key（如 learning-ds）"
            value={datasetKey}
            onChange={(event) => setDatasetKey(event.target.value)}
          />
          <input
            className="w-full rounded border px-2 py-1"
            placeholder="task_type"
            value={taskType}
            onChange={(event) => setTaskType(event.target.value)}
          />
          <button
            type="button"
            className="rounded bg-primary px-3 py-1.5 text-primary-foreground"
            onClick={() => void createDataset()}
          >
            创建数据集
          </button>
          {datasetId ? (
            <p className="font-mono text-xs text-muted-foreground">dataset_id: {datasetId}</p>
          ) : null}
        </div>

        <div className="space-y-2 rounded-lg border p-4 text-sm">
          <h2 className="font-medium">2. 样本（≥30 才可用于门禁）</h2>
          <input
            className="w-full rounded border px-2 py-1"
            placeholder="sample_id"
            value={sample.sample_id}
            onChange={(event) => setSample({ ...sample, sample_id: event.target.value })}
          />
          <input
            className="w-full rounded border px-2 py-1"
            placeholder="golden labels（逗号分隔）"
            value={sample.labels}
            onChange={(event) => setSample({ ...sample, labels: event.target.value })}
          />
          <input
            className="w-full rounded border px-2 py-1"
            placeholder="labeler"
            value={sample.labeler}
            onChange={(event) => setSample({ ...sample, labeler: event.target.value })}
          />
          <div className="flex gap-2">
            <button
              type="button"
              className="rounded border px-3 py-1 hover:bg-muted/40"
              onClick={() => void addSample()}
              disabled={!datasetId}
            >
              追加样本
            </button>
            <button
              type="button"
              className="rounded border px-3 py-1 hover:bg-muted/40"
              onClick={() => void freeze()}
              disabled={!datasetId}
            >
              冻结数据集
            </button>
            <button
              type="button"
              className="rounded bg-primary px-3 py-1 text-primary-foreground"
              onClick={() => void execute()}
              disabled={!datasetId || running}
            >
              {running ? '运行中…' : '运行 LLM Benchmark'}
            </button>
          </div>
          {frozen ? (
            <div className="space-y-1 text-xs">
              <p>样本数：{frozen.sample_count}</p>
              <p className="font-mono">hash: {frozen.content_hash.slice(0, 24)}…</p>
              <Badge tone={frozen.gate_eligible ? 'success' : 'warning'}>
                {frozen.gate_eligible ? '可用于门禁' : '仅参考（<30）'}
              </Badge>
            </div>
          ) : null}
        </div>
      </section>

      <section className="space-y-2 rounded-lg border p-4 text-sm">
        <h2 className="font-medium">3. 查看 BenchmarkRun 结果</h2>
        <div className="flex gap-2">
          <input
            className="w-full rounded border px-2 py-1 font-mono"
            placeholder="benchmark run id"
            value={runId}
            onChange={(event) => setRunId(event.target.value)}
          />
          <button
            type="button"
            className="rounded border px-3 py-1 hover:bg-muted/40"
            onClick={() => void loadRun()}
          >
            查询
          </button>
        </div>
        {run ? (
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <Badge tone={run.result_status === 'PASS_GATE' ? 'success' : 'warning'}>
                {run.result_status || run.status}
              </Badge>
              <span className="text-xs text-muted-foreground">{run.agent_key}</span>
            </div>
            <pre className="max-h-64 overflow-auto whitespace-pre-wrap rounded bg-muted/30 p-2 text-xs">
              {JSON.stringify(run.metrics, null, 2)}
            </pre>
            <p className="text-xs text-muted-foreground">
              逐样本结果：{run.per_sample?.length ?? 0} 条
            </p>
          </div>
        ) : null}
      </section>
    </div>
  )
}
