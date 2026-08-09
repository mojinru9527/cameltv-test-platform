/** C102-4 — 生产页面 vs 需求原型差异标注面板（Batch 119）。
 *
 * 复用 POST /requirement-modules/production-diff：选择发布包 + 粘贴生产页面
 * 清单（每行一个 label），生成 new/matched/missing 差异标注。
 */
import { useCallback, useEffect, useState } from 'react'
import { toast } from 'sonner'
import { getCaptureTask, listReleaseBundles, productionDiff } from '@/api/requirement'
import type { ProductionDiffResult, ReleaseBundleBrief } from '@/types'
import { Button } from '@/ui'
import { Badge } from '@/ui'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select'
import { GitCompare, Loader2 } from '@/lib/icons'

const CHANGE_TYPE_LABEL: Record<string, string> = {
  new: '新增',
  matched: '一致',
  missing: '缺失',
}

const CHANGE_TYPE_CLASS: Record<string, string> = {
  new: 'border-status-info-border bg-status-info-muted text-status-info',
  matched: 'border-status-success-border bg-status-success-muted text-status-success',
  missing: 'border-status-warning-border bg-status-warning-muted text-status-warning',
}

export default function ProductionDiffPanel() {
  const [bundles, setBundles] = useState<ReleaseBundleBrief[]>([])
  const [bundleId, setBundleId] = useState<string>('')
  const [labels, setLabels] = useState('')
  const [loading, setLoading] = useState(true)
  const [generating, setGenerating] = useState(false)
  const [captureTaskId, setCaptureTaskId] = useState('')
  const [loadingCapture, setLoadingCapture] = useState(false)
  const [result, setResult] = useState<ProductionDiffResult | null>(null)
  const [error, setError] = useState('')

  const loadBundles = useCallback(async (signal?: AbortSignal) => {
    setLoading(true)
    try {
      const data = await listReleaseBundles(signal)
      if (signal?.aborted) return
      const items = data.items || []
      setBundles(items)
      if (items.length > 0) setBundleId((current) => current || String(items[0].id))
    } catch (e) {
      if (!signal?.aborted) setError(e instanceof Error ? e.message : '发布包加载失败')
    } finally {
      if (!signal?.aborted) setLoading(false)
    }
  }, [])

  useEffect(() => {
    const controller = new AbortController()
    void loadBundles(controller.signal)
    return () => controller.abort()
  }, [loadBundles])

  const pageToLabel = (url: string): string => {
    const clean = url.replace(/^https?:\/\//, '').split('?')[0].replace(/\/$/, '')
    return clean
  }

  const handleLoadCapture = async () => {
    const taskId = captureTaskId.trim()
    if (!taskId) {
      toast.warning('请输入采集任务 ID')
      return
    }
    setLoadingCapture(true)
    setError('')
    try {
      const task = await getCaptureTask(taskId)
      if (task.status !== 'done') {
        toast.warning('采集任务尚未完成，请稍后再试')
        return
      }
      const pages = task.pages || []
      if (pages.length === 0) {
        toast.warning('该采集任务无页面清单')
        return
      }
      setLabels(pages.map(pageToLabel).join('\n'))
      toast.success(`已加载 ${pages.length} 个生产页面`)
    } catch (e) {
      const msg = e instanceof Error ? e.message : '采集任务加载失败'
      setError(msg)
      toast.error(msg)
    } finally {
      setLoadingCapture(false)
    }
  }

  const handleGenerate = async () => {
    if (!bundleId) {
      toast.warning('请先选择发布包')
      return
    }
    const pages = labels.split('\n').map((s) => s.trim()).filter(Boolean)
    if (pages.length === 0) {
      toast.warning('请粘贴生产页面清单（每行一个）')
      return
    }
    setGenerating(true)
    setError('')
    try {
      const data = await productionDiff(Number(bundleId), pages.map((label) => ({ label })))
      setResult(data)
    } catch (e) {
      const msg = e instanceof Error ? e.message : '差异生成失败'
      setError(msg)
      toast.error(msg)
    } finally {
      setGenerating(false)
    }
  }

  return (
    <Card size="sm" className="ui-surface">
      <CardHeader className="border-b pb-3">
        <CardTitle className="text-sm flex items-center gap-2">
          <GitCompare className="size-4" />
          生产差异标注（C102-4）
        </CardTitle>
      </CardHeader>
      <CardContent className="pt-4 space-y-3">
        {loading ? (
          <div className="space-y-2">
            <Skeleton className="h-8 w-full" />
            <Skeleton className="h-20 w-full" />
          </div>
        ) : (
          <>
            <div className="grid gap-2 sm:grid-cols-[240px_1fr]">
              <div className="space-y-1.5">
                <Label htmlFor="diff-bundle" className="text-xs">发布包</Label>
                <Select value={bundleId} onValueChange={setBundleId}>
                  <SelectTrigger id="diff-bundle" className="h-8" aria-label="选择发布包">
                    <SelectValue placeholder="选择发布包" />
                  </SelectTrigger>
                  <SelectContent>
                    {bundles.map((b) => (
                      <SelectItem key={b.id} value={String(b.id)}>
                        {b.name}（{b.client_version || b.status}）
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="diff-labels" className="text-xs">生产页面清单（每行一个）</Label>
                <Textarea
                  id="diff-labels"
                  rows={3}
                  placeholder={'例如：\nmatch-replay\nworldcup-2026\n资讯列表'}
                  value={labels}
                  onChange={(e) => setLabels(e.target.value)}
                />
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Input
                className="h-8 max-w-[240px]"
                placeholder="采集任务 ID（/ui-tests/capture）"
                value={captureTaskId}
                onChange={(e) => setCaptureTaskId(e.target.value)}
                aria-label="采集任务 ID"
              />
              <Button size="sm" variant="secondary" onClick={handleLoadCapture} disabled={loadingCapture}>
                {loadingCapture && <Loader2 className="size-3.5 animate-spin" />}
                加载采集
              </Button>
              <Button size="sm" onClick={handleGenerate} disabled={generating}>
                {generating && <Loader2 className="size-3.5 animate-spin" />}
                生成差异
              </Button>
              {result && (
                <div className="flex items-center gap-2 flex-wrap text-xs">
                  <Badge tone="neutral" className="border-status-info-border bg-status-info-muted text-status-info">
                    新增 {result.summary.new_count}
                  </Badge>
                  <Badge tone="neutral" className="border-status-success-border bg-status-success-muted text-status-success">
                    一致 {result.summary.matched_count}
                  </Badge>
                  <Badge tone="neutral" className="border-status-warning-border bg-status-warning-muted text-status-warning">
                    缺失 {result.summary.missing_count}
                  </Badge>
                  <span className="text-muted-foreground">
                    生产 {result.summary.production_total} · 需求 {result.summary.requirement_total}
                  </span>
                </div>
              )}
            </div>
            {error && <p className="text-xs text-status-danger">{error}</p>}
            {result && (
              <div className="border rounded-lg overflow-auto max-h-[220px]">
                {result.items.length === 0 ? (
                  <p className="text-xs text-muted-foreground py-4 text-center">暂无差异项</p>
                ) : (
                  <ul className="divide-y">
                    {result.items.slice(0, 50).map((item, i) => (
                      <li key={`${item.name}-${i}`} className="flex items-center gap-2 px-3 py-1.5">
                        <Badge tone="neutral" className={CHANGE_TYPE_CLASS[item.change_type] || 'border-border bg-muted text-muted-foreground'}>
                          {CHANGE_TYPE_LABEL[item.change_type] || item.change_type}
                        </Badge>
                        <span className="text-xs truncate">{item.name}</span>
                        {item.matched_with && (
                          <span className="text-[11px] text-muted-foreground ml-auto">匹配: {item.matched_with}</span>
                        )}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            )}
          </>
        )}
      </CardContent>
    </Card>
  )
}
