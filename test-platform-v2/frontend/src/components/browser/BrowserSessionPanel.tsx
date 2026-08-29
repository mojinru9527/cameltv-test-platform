import { useState } from 'react'
import { Badge, Button, Input } from '@/ui'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { toast } from 'sonner'
import { Play, Square } from '@/lib/icons'
import {
  startBrowserSession,
  stopBrowserSession,
  type BrowserSession,
  type BrowserSessionMode,
} from '@/api/browserInteractions'

export interface BrowserSessionPanelProps {
  missionId: number
  /** Default environment to pre-fill; the user may change it. */
  environmentId?: number | null
  mode?: BrowserSessionMode | string
  onSession?: (session: BrowserSession | null) => void
}

const MODE_OPTIONS: BrowserSessionMode[] = ['OBSERVE', 'EXPLORE', 'REGRESSION', 'MANUAL_ASSIST']

/**
 * Start / stop a browser session (Observe) for a mission. The panel owns the
 * session lifecycle and reports it upward so the page can poll events.
 */
export function BrowserSessionPanel({
  missionId,
  environmentId,
  mode = 'OBSERVE',
  onSession,
}: BrowserSessionPanelProps) {
  const [selectedMode, setSelectedMode] = useState<BrowserSessionMode | string>(mode)
  const [envInput, setEnvInput] = useState(environmentId !== null && environmentId !== undefined ? String(environmentId) : '')
  const [browserType, setBrowserType] = useState('')
  const [contextRef, setContextRef] = useState('')
  const [session, setSession] = useState<BrowserSession | null>(null)
  const [starting, setStarting] = useState(false)
  const [stopping, setStopping] = useState(false)

  const canStart = missionId > 0 && envInput.trim() !== '' && !starting

  const doStart = async () => {
    const envId = Number(envInput)
    if (!missionId || !envId) return
    setStarting(true)
    try {
      const created = await startBrowserSession({
        mission_id: missionId,
        environment_id: envId,
        mode: selectedMode,
        browser_type: browserType || undefined,
        context_ref: contextRef || undefined,
      })
      setSession(created)
      onSession?.(created)
      toast.success(`浏览器会话 ${created.id} 已启动`)
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '启动会话失败')
    } finally {
      setStarting(false)
    }
  }

  const doStop = async () => {
    if (!session) return
    setStopping(true)
    try {
      const stopped = await stopBrowserSession(session.id)
      setSession(stopped)
      onSession?.(stopped)
      toast.success('浏览器会话已停止')
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '停止会话失败')
    } finally {
      setStopping(false)
    }
  }

  const resetSession = () => {
    setSession(null)
    onSession?.(null)
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>浏览器会话 (Observe)</CardTitle>
        <CardDescription>
          启动一个浏览器会话以捕获观察事件（semantic target / XHR / 证据）。
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {session ? (
          <div className="space-y-3">
            <div className="flex flex-wrap items-center gap-2 text-sm">
              <span className="font-mono">{session.id}</span>
              <Badge tone={session.status === 'ACTIVE' ? 'success' : 'neutral'}>{session.status}</Badge>
              <Badge variant="outline">{session.mode}</Badge>
            </div>
            <div className="flex gap-2">
              <Button variant="secondary" onClick={doStop} disabled={stopping}>
                <Square className="size-3.5" /> {stopping ? '停止中…' : '停止会话'}
              </Button>
              <Button variant="ghost" onClick={resetSession}>新会话</Button>
            </div>
          </div>
        ) : (
          <div className="space-y-3">
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="space-y-1.5">
                <label htmlFor="bs-mode" className="text-xs font-medium text-muted-foreground">会话模式</label>
                <Select value={selectedMode} onValueChange={(v) => setSelectedMode(v)}>
                  <SelectTrigger id="bs-mode">
                    <SelectValue placeholder="选择模式" />
                  </SelectTrigger>
                  <SelectContent>
                    {MODE_OPTIONS.map((m) => (
                      <SelectItem key={m} value={m}>{m}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1.5">
                <label htmlFor="bs-env" className="text-xs font-medium text-muted-foreground">环境 ID</label>
                <Input
                  id="bs-env"
                  type="number"
                  value={envInput}
                  onChange={(e) => setEnvInput(e.target.value)}
                  placeholder="如 1"
                />
              </div>
              <div className="space-y-1.5">
                <label htmlFor="bs-browser" className="text-xs font-medium text-muted-foreground">浏览器类型（可选）</label>
                <Input
                  id="bs-browser"
                  value={browserType}
                  onChange={(e) => setBrowserType(e.target.value)}
                  placeholder="chromium / firefox"
                />
              </div>
              <div className="space-y-1.5">
                <label htmlFor="bs-context" className="text-xs font-medium text-muted-foreground">上下文引用（可选）</label>
                <Input
                  id="bs-context"
                  value={contextRef}
                  onChange={(e) => setContextRef(e.target.value)}
                  placeholder="context_ref"
                />
              </div>
            </div>
            <Button onClick={doStart} disabled={!canStart}>
              <Play className="size-4" /> {starting ? '启动中…' : '启动浏览器会话'}
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
