import { useState } from 'react'
import { Badge, Button, Input } from '@/ui'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { toast } from 'sonner'
import { Zap } from '@/lib/icons'
import { runHybrid, type HybridRunResult } from '@/api/browserInteractions'
import { JsonBlock } from './JsonView'

export interface HybridRunLauncherProps {
  scenarioId: number
  scenarioVersionId?: number | null
}

/**
 * Launches a hybrid (human-in-the-loop) run for a scenario and renders the
 * resulting data-preparation, action, oracle and cleanup outcome.
 */
export function HybridRunLauncher({ scenarioId }: HybridRunLauncherProps) {
  const [runId, setRunId] = useState('')
  const [running, setRunning] = useState(false)
  const [result, setResult] = useState<HybridRunResult | null>(null)

  const doRun = async () => {
    const runIdNum = Number(runId)
    if (!runIdNum) {
      toast.error('请输入 run_id')
      return
    }
    setRunning(true)
    try {
      const res = await runHybrid(scenarioId, { run_id: runIdNum })
      setResult(res)
      toast.success('Hybrid 运行完成')
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Hybrid 运行失败')
    } finally {
      setRunning(false)
    }
  }

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>Hybrid Run（人工在环）</CardTitle>
          <CardDescription>
            输入 run_id 执行一次混合运行，观察数据准备 / 动作 / 验证 / 清理结果。
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-wrap items-end gap-2">
          <div className="w-48 space-y-1.5">
            <label htmlFor="hybrid-run-id" className="text-xs font-medium text-muted-foreground">run_id</label>
            <Input
              id="hybrid-run-id"
              type="number"
              value={runId}
              onChange={(e) => setRunId(e.target.value)}
              placeholder="执行运行 ID"
            />
          </div>
          <Button onClick={doRun} disabled={running}>
            <Zap className="size-4" /> {running ? '运行中…' : '运行'}
          </Button>
        </CardContent>
      </Card>

      {result && (
        <div className="space-y-4">
          <div className="grid gap-4 lg:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  数据准备
                  {result.data.prepared ? (
                    <Badge tone="success">已就绪</Badge>
                  ) : (
                    <Badge tone="warning">未就绪</Badge>
                  )}
                </CardTitle>
              </CardHeader>
              <CardContent>
                {result.data.reason ? (
                  <p className="text-sm text-muted-foreground">{result.data.reason}</p>
                ) : (
                  <p className="text-sm text-muted-foreground">数据已准备，无需说明。</p>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>清理 (cleanup)</CardTitle>
              </CardHeader>
              <CardContent>
                <JsonBlock data={result.cleanup} />
              </CardContent>
            </Card>
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>执行动作 (action)</CardTitle>
              </CardHeader>
              <CardContent>
                <JsonBlock data={result.action} />
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>验证 (oracle)</CardTitle>
              </CardHeader>
              <CardContent>
                <JsonBlock data={result.oracle} />
              </CardContent>
            </Card>
          </div>
        </div>
      )}
    </div>
  )
}
