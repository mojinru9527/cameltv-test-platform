import { useEffect, useState } from 'react'
import { useParams } from 'react-router'
import { Badge, Button, Card, CardContent, CardDescription, CardHeader, CardTitle, PageShell, Progress } from '@/ui'
import { createDefectDraft, getVersionTask, listRuns, startRun, type VersionTask, type VersionTaskRun } from '@/api/versionTask'
import { toast } from 'sonner'

/** B8 版本任务执行与证据：一键运行 → 进度 → 证据回放 → 失败分类转缺陷草稿。 */
export default function VersionTaskRunPage() {
  const { taskId } = useParams()
  const id = Number(taskId)
  const [task, setTask] = useState<VersionTask | null>(null)
  const [runs, setRuns] = useState<VersionTaskRun[]>([])
  const [loading, setLoading] = useState(false)

  async function refresh() {
    if (!Number.isFinite(id)) return
    try {
      const [t, rs] = await Promise.all([getVersionTask(id), listRuns(id)])
      setTask(t)
      setRuns(rs)
    } catch (e) {
      toast.error((e as Error).message || '加载失败')
    }
  }

  useEffect(() => {
    void refresh()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id])

  async function handleRun() {
    setLoading(true)
    try {
      const run = await startRun(id)
      toast.success(`运行完成：${run.passed} 通过 / ${run.failed} 失败`)
      await refresh()
    } catch (e) {
      toast.error((e as Error).message || '运行失败')
    } finally {
      setLoading(false)
    }
  }

  async function handleDefect(run: VersionTaskRun, idx: number) {
    try {
      const d = await createDefectDraft(id, run.id, idx)
      toast.success(`已转缺陷草稿 #${d.defect_id}`)
    } catch (e) {
      toast.error((e as Error).message || '转缺陷失败')
    }
  }

  const latest = runs[0]

  return (
    <PageShell title={task ? `版本验收 · ${task.title}` : '版本验收'}>
      <Card>
        <CardHeader>
          <CardTitle>执行与证据</CardTitle>
          <CardDescription>{task ? `${task.version} · 状态 ${task.status}` : ''}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center gap-2">
            <Button variant="primary" onClick={handleRun} disabled={loading}>一键运行</Button>
            <Badge variant="secondary">覆盖 {latest ? `${latest.passed}/${latest.total}` : '—'}</Badge>
          </div>

          {latest && (
            <div className="space-y-3">
              <Progress value={latest.progress} className="h-2" />
              <div className="flex gap-3 text-sm">
                <Badge variant="secondary">通过 {latest.passed}</Badge>
                <Badge variant="destructive">失败 {latest.failed}</Badge>
                <Badge variant="secondary">跳过 {latest.skipped}</Badge>
                <Badge variant="secondary">阻塞 {latest.blocked}</Badge>
              </div>

              {latest.failures.length > 0 && (
                <div className="space-y-1">
                  <h3 className="text-sm font-medium">失败分类</h3>
                  {latest.failures.map((f, idx) => (
                    <div key={idx} className="rounded border p-2 text-sm">
                      <div className="flex items-center gap-2">
                        <Badge variant="destructive">{f.kind}</Badge>
                        <span>{f.title}</span>
                        <Button size="sm" variant="secondary" className="ml-auto" onClick={() => handleDefect(latest, idx)}>转缺陷草稿</Button>
                      </div>
                      <p className="mt-1 text-xs text-muted-foreground">{f.message} · 证据 {f.evidence}</p>
                    </div>
                  ))}
                </div>
              )}

              {latest.evidence.length > 0 && (
                <div className="space-y-1">
                  <h3 className="text-sm font-medium">证据回放</h3>
                  {latest.evidence.slice(0, 8).map((e, idx) => (
                    <div key={idx} className="flex items-center gap-2 text-xs text-muted-foreground">
                      <Badge variant={e.status === 'pass' ? 'secondary' : 'destructive'}>{e.status}</Badge>
                      <span>{e.ref}</span>
                      <span className="ml-auto">查看 {e.url}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>
    </PageShell>
  )
}
