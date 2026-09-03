import { useEffect, useState } from 'react'
import { useParams } from 'react-router'
import { Badge, Button, Card, CardContent, CardDescription, CardHeader, CardTitle, Input, PageShell, Progress } from '@/ui'
import { buildReleasePackage, createDefectDraft, getRegressionSet, getVersionTask, listRuns, notifyRelease, releaseTask, startRun, syncDefect, type RegressionItem, type ReleasePackage, type VersionTask, type VersionTaskRun } from '@/api/versionTask'
import { toast } from 'sonner'

const TASK_STATUS_LABEL: Record<string, string> = {
  draft: '草稿',
  plan_review: '待评审',
  approved: '已批准',
  executing: '执行中',
  executed: '已执行',
  verdict: '待结论',
  released: '已结束',
  blocked: '已阻塞',
  cancelled: '已取消',
}

export function isPassVerdictAllowed(run?: VersionTaskRun): boolean {
  return Boolean(run && run.passed > 0 && run.failed === 0 && run.skipped === 0 && run.blocked === 0)
}

/** B8 版本任务执行与证据：一键运行 → 进度 → 证据回放 → 失败分类转缺陷草稿。 */
export default function VersionTaskRunPage() {
  const { taskId } = useParams()
  const id = Number(taskId)
  const [task, setTask] = useState<VersionTask | null>(null)
  const [runs, setRuns] = useState<VersionTaskRun[]>([])
  const [loading, setLoading] = useState(false)
  const [defectIds, setDefectIds] = useState<Record<string, number>>({})

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
    let cancelled = false
    Promise.all([getVersionTask(id), listRuns(id)])
      .then(([nextTask, nextRuns]) => {
        if (!cancelled) {
          setTask(nextTask)
          setRuns(nextRuns)
        }
      })
      .catch((error: Error) => {
        if (!cancelled) toast.error(error.message || '加载失败')
      })
    return () => { cancelled = true }
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
      setDefectIds((current) => ({ ...current, [`${run.id}:${idx}`]: d.defect_id }))
      toast.success(`已转缺陷草稿 #${d.defect_id}`)
    } catch (e) {
      toast.error((e as Error).message || '转缺陷失败')
    }
  }

  async function handleSync(run: VersionTaskRun, idx: number) {
    const defectId = defectIds[`${run.id}:${idx}`]
    if (!defectId) return
    try {
      await syncDefect(id, defectId)
      toast.success(`缺陷 #${defectId} 已同步`)
    } catch (e) {
      toast.error((e as Error).message || '同步失败')
    }
  }

  const latest = runs[0]
  const [pkg, setPkg] = useState<ReleasePackage | null>(null)
  const [bundleId, setBundleId] = useState('')
  const [regression, setRegression] = useState<RegressionItem[]>([])
  useEffect(() => {
    let cancelled = false
    getRegressionSet(id).then((items) => { if (!cancelled) setRegression(items) }).catch(() => {})
    return () => { cancelled = true }
  }, [id])

  useEffect(() => {
    let cancelled = false
    buildReleasePackage(id).then((next) => { if (!cancelled) setPkg(next) }).catch(() => {})
    return () => { cancelled = true }
  }, [id])

  async function handleRelease(verdict: string) {
    try {
      const risk = window.prompt('风险点（逗号分隔，可留空）') ?? ''
      const p = await releaseTask(id, verdict, bundleId ? Number(bundleId) : undefined, risk.split(',').map((x) => x.trim()).filter(Boolean))
      setPkg(p)
      toast.success(`已${verdict === 'pass' ? '放行' : verdict === 'blocked' ? '打回' : '有条件放行'}`)
    } catch (e) {
      toast.error((e as Error).message || '放行失败')
    }
  }

  async function handleNotify() {
    try { await notifyRelease(id); toast.success('通知已发送') } catch (e) { toast.error((e as Error).message || '通知失败') }
  }

  return (
    <PageShell title={task ? `版本验收 · ${task.title}` : '版本验收'}>
      <Card>
        <CardHeader>
          <CardTitle>执行与证据</CardTitle>
          <CardDescription>{task ? `${task.version} · 状态 ${TASK_STATUS_LABEL[task.status] || task.status}` : ''}</CardDescription>
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
                        <Button size="sm" variant="ghost" disabled={!defectIds[`${latest.id}:${idx}`]} onClick={() => handleSync(latest, idx)}>同步缺陷库</Button>
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

      <Card className="mt-4">
        <CardHeader>
          <CardTitle>放行结论</CardTitle>
          <CardDescription>基于覆盖/通过率/风险生成可分享放行证据包</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {pkg && (
            <div className="space-y-2 text-sm">
              <div className="flex gap-3">
                <Badge variant="secondary">通过率 {pkg.pass_rate}%</Badge>
                <Badge variant="secondary">总校验 {pkg.total_checks}</Badge>
                <Badge variant={pkg.verdict === 'blocked' ? 'destructive' : 'outline'}>结论 {pkg.verdict || '—'}</Badge>
              </div>
              {pkg.risk.length > 0 && <p className="text-xs text-muted-foreground">风险：{pkg.risk.join('、')}</p>}
            </div>
          )}
          <div className="flex flex-wrap items-center gap-2">
            <Input className="w-32" placeholder="发布包 ID" value={bundleId} onChange={(e) => setBundleId(e.target.value)} />
            <Button variant="primary" disabled={!isPassVerdictAllowed(latest)} onClick={() => handleRelease('pass')}>放行</Button>
            <Button variant="secondary" onClick={() => handleRelease('conditional')}>有条件放行</Button>
            <Button variant="danger" onClick={() => handleRelease('blocked')}>打回</Button>
            <Button variant="ghost" onClick={handleNotify}>发送通知</Button>
          </div>
          {latest && !isPassVerdictAllowed(latest) && (
            <p className="text-xs text-muted-foreground">存在失败、跳过或阻塞检查时不能直接放行，可选择有条件放行或打回。</p>
          )}
        </CardContent>
      </Card>

      <Card className="mt-4">
        <CardHeader>
          <CardTitle>推荐回归集</CardTitle>
          <CardDescription>基于变更模块 / 方案条目 / 上版复用的影响面推荐</CardDescription>
        </CardHeader>
        <CardContent className="space-y-1">
          {regression.length === 0 && <p className="text-sm text-muted-foreground">暂无推荐回归集。</p>}
          {regression.map((it, idx) => (
            <div key={idx} className="flex items-center gap-2 rounded border p-2 text-sm">
              <Badge variant={it.priority === 'P0' ? 'destructive' : 'secondary'}>{it.priority}</Badge>
              <span className="text-xs text-muted-foreground">{it.kind}</span>
              <span>{it.title}</span>
              <span className="ml-auto text-xs text-muted-foreground">{it.source}</span>
            </div>
          ))}
        </CardContent>
      </Card>
    </PageShell>
  )
}
