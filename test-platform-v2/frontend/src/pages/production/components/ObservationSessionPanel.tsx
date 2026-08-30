import { useCallback, useState } from 'react'
import { toast } from 'sonner'
import { Badge, Button, Card, CardContent, CardHeader, CardTitle, Input, Label, Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/ui'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import {
  fetchObservationSession,
  startObservationSession,
  stopObservationSession,
  OBSERVATION_MODE_LABELS,
  SESSION_STATUS_LABELS,
  type ObservationSession,
} from '@/api/production'
import { StopCircle, Play, RefreshCw } from '@/lib/icons'

const MODES = Object.keys(OBSERVATION_MODE_LABELS)

interface ObservationSessionPanelProps {
  projectId: number | null
  environmentId?: number | null
  missionId?: number | null
  defaultMode?: string
  /** Called after a session starts or stops; lets the parent refresh journey data. */
  onChange?: (session: ObservationSession | null) => void
}

/**
 * Start / stop a production-observation session and display its status + mode.
 */
export function ObservationSessionPanel({
  projectId,
  environmentId,
  missionId,
  defaultMode = 'OBSERVE',
  onChange,
}: ObservationSessionPanelProps) {
  useDocumentTitle('生产证据')
  const [session, setSession] = useState<ObservationSession | null>(null)
  const [mode, setMode] = useState(defaultMode)
  const [envId, setEnvId] = useState<string>(environmentId ? String(environmentId) : '')
  const [workerId, setWorkerId] = useState<string>('')
  const [starting, setStarting] = useState(false)
  const [stopping, setStopping] = useState(false)

  const handleStart = useCallback(async () => {
    if (!projectId) {
      toast.error('缺少项目上下文（project_id）')
      return
    }
    const environment_id = Number(envId)
    if (!Number.isFinite(environment_id) || environment_id <= 0) {
      toast.error('请选择环境（environment_id）')
      return
    }
    setStarting(true)
    try {
      const { id } = await startObservationSession({
        project_id: projectId,
        environment_id,
        mission_id: missionId ?? null,
        worker_id: workerId ? Number(workerId) : null,
        mode,
      })
      const detail = await fetchObservationSession(id)
      setSession(detail)
      onChange?.(detail)
      toast.success('观察会话已启动')
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '启动失败')
    } finally {
      setStarting(false)
    }
  }, [projectId, envId, missionId, mode, workerId, onChange])

  const handleStop = useCallback(async () => {
    if (!session) return
    setStopping(true)
    try {
      await stopObservationSession(session.id)
      const detail = await fetchObservationSession(session.id)
      setSession(detail)
      onChange?.(detail)
      toast.success('观察会话已停止')
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '停止失败')
    } finally {
      setStopping(false)
    }
  }, [session, onChange])

  const statusMeta = session ? SESSION_STATUS_LABELS[session.status] : undefined
  const modeMeta = session ? OBSERVATION_MODE_LABELS[session.mode] : undefined

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex flex-wrap items-center gap-2">
          观察会话
          {session && <Badge tone="neutral" className={statusMeta?.color}>{statusMeta?.label ?? session.status}</Badge>}
          {session && <Badge tone="neutral" className={modeMeta?.color}>{modeMeta?.label ?? session.mode}</Badge>}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {!session && (
          <div className="grid gap-3 sm:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_minmax(0,1fr)_auto]">
            <div className="space-y-1.5">
              <Label>模式</Label>
              <Select value={mode} onValueChange={setMode}>
                <SelectTrigger>
                  <SelectValue placeholder="选择模式" />
                </SelectTrigger>
                <SelectContent>
                  {MODES.map((m) => (
                    <SelectItem key={m} value={m}>{OBSERVATION_MODE_LABELS[m]?.label ?? m}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label>环境 ID</Label>
              <Input
                value={envId}
                onChange={(e) => setEnvId(e.target.value)}
                placeholder="environment_id"
                inputMode="numeric"
              />
            </div>
            <div className="space-y-1.5">
              <Label>Worker ID（可选）</Label>
              <Input
                value={workerId}
                onChange={(e) => setWorkerId(e.target.value)}
                placeholder="worker_id"
                inputMode="numeric"
              />
            </div>
            <div className="flex items-end">
              <Button variant="primary" size="sm" onClick={() => void handleStart()} disabled={starting}>
                <Play className="size-3.5" /> {starting ? '启动中…' : '启动观察'}
              </Button>
            </div>
          </div>
        )}

        {session && (
          <div className="space-y-3">
            <dl className="grid grid-cols-2 gap-x-4 gap-y-1 text-sm sm:grid-cols-3">
              <div>
                <dt className="text-xs text-muted-foreground">Session</dt>
                <dd className="font-mono">#{session.id}</dd>
              </div>
              <div>
                <dt className="text-xs text-muted-foreground">项目</dt>
                <dd className="font-mono">#{session.project_id}</dd>
              </div>
              <div>
                <dt className="text-xs text-muted-foreground">环境</dt>
                <dd className="font-mono">#{session.environment_id}</dd>
              </div>
              <div>
                <dt className="text-xs text-muted-foreground">模式</dt>
                <dd>{modeMeta?.label ?? session.mode}</dd>
              </div>
              <div>
                <dt className="text-xs text-muted-foreground">策略版本</dt>
                <dd className="font-mono">{session.policy_version ?? '-'}</dd>
              </div>
              <div>
                <dt className="text-xs text-muted-foreground">开始时间</dt>
                <dd>{session.started_at ? new Date(session.started_at).toLocaleString() : '-'}</dd>
              </div>
            </dl>
            <div className="flex items-center gap-2">
              <Button variant="secondary" size="sm" onClick={() => void handleStop()} disabled={stopping || session.status !== 'ACTIVE'}>
                <StopCircle className="size-3.5" /> {stopping ? '停止中…' : '停止会话'}
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => fetchObservationSession(session.id).then(setSession).catch(() => undefined)}
              >
                <RefreshCw className="size-3.5" /> 刷新
              </Button>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
