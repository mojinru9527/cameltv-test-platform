import { useEffect, useState, type FormEvent } from 'react'
import {
  Badge,
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Input,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/ui'
import {
  createNoiseRule,
  deleteNoiseRule,
  listNoiseRules,
  renewNoiseRule,
  type NoiseRule,
} from '@/api/aiqeConsole'
import { cn } from '@/lib/utils'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import ConsoleTabs from './ConsoleTabs'

const ACTIONS = [
  { value: 'suppress', label: 'suppress（静默）' },
  { value: 'hint', label: 'hint（提示）' },
  { value: 'quarantine', label: 'quarantine（隔离，必须有到期）' },
] as const

const EXPIRING_DAYS = 7

function errorText(err: unknown): string {
  return err instanceof Error ? err.message : '请求失败'
}

function daysUntil(value: string): number {
  return Math.ceil((new Date(value).getTime() - Date.now()) / 86_400_000)
}

export default function NoiseRulesPage() {
  useDocumentTitle('噪音规则')
  const [rules, setRules] = useState<NoiseRule[]>([])
  const [pattern, setPattern] = useState('')
  const [action, setAction] = useState<string>('suppress')
  const [expiresAt, setExpiresAt] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    let alive = true
    listNoiseRules()
      .then((rows) => {
        if (alive) setRules(rows)
      })
      .catch((err: unknown) => {
        if (alive) setError(errorText(err))
      })
    return () => {
      alive = false
    }
  }, [])

  async function handleCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const trimmed = pattern.trim()
    if (!trimmed || busy) return
    setBusy(true)
    setError('')
    try {
      const created = await createNoiseRule({
        pattern: trimmed,
        action,
        scope: 'run',
        ...(expiresAt ? { expires_at: new Date(expiresAt).toISOString() } : {}),
      })
      setRules((prev) => [created, ...prev])
      setPattern('')
      setExpiresAt('')
    } catch (err: unknown) {
      setError(errorText(err))
    } finally {
      setBusy(false)
    }
  }

  async function handleRenew(rule: NoiseRule) {
    setError('')
    try {
      const updated = await renewNoiseRule(rule.id)
      setRules((prev) => prev.map((row) => (row.id === updated.id ? updated : row)))
    } catch (err: unknown) {
      setError(errorText(err))
    }
  }

  async function handleDelete(rule: NoiseRule) {
    setError('')
    try {
      await deleteNoiseRule(rule.id)
      setRules((prev) => prev.filter((row) => row.id !== rule.id))
    } catch (err: unknown) {
      setError(errorText(err))
    }
  }

  return (
    <div className="space-y-4 p-6">
      <header className="space-y-3">
        <div>
          <h1 className="text-2xl font-semibold">噪音规则</h1>
          <p className="text-sm text-muted-foreground">
            最长 90 天强制复核；临期 7 天内与已过期规则标红。
          </p>
        </div>
        <ConsoleTabs />
      </header>

      {error ? <p className="text-sm text-destructive">{error}</p> : null}

      <Card>
        <CardHeader>
          <CardTitle className="text-base">新建规则</CardTitle>
        </CardHeader>
        <CardContent>
          <form className="flex flex-wrap items-end gap-3" onSubmit={handleCreate}>
            <label className="space-y-1 text-sm">
              <span className="text-muted-foreground">pattern</span>
              <Input
                aria-label="规则 pattern"
                className="w-60"
                onChange={(event) => setPattern(event.target.value)}
                placeholder="例如：广告弹窗遮挡"
                value={pattern}
              />
            </label>
            <label className="space-y-1 text-sm">
              <span className="text-muted-foreground">action</span>
              <Select onValueChange={setAction} value={action}>
                <SelectTrigger aria-label="规则 action" className="w-64">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {ACTIONS.map((item) => (
                    <SelectItem key={item.value} value={item.value}>
                      {item.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </label>
            <label className="space-y-1 text-sm">
              <span className="text-muted-foreground">到期时间（可选）</span>
              <Input
                aria-label="到期时间"
                className="w-48"
                onChange={(event) => setExpiresAt(event.target.value)}
                type="datetime-local"
                value={expiresAt}
              />
            </label>
            <Button disabled={busy || !pattern.trim()} type="submit">
              {busy ? '创建中…' : '创建'}
            </Button>
          </form>
        </CardContent>
      </Card>

      <div className="overflow-hidden rounded-lg border">
        <table className="w-full text-sm">
          <thead className="bg-muted/40 text-left">
            <tr>
              <th className="px-3 py-2">pattern</th>
              <th className="px-3 py-2">action</th>
              <th className="px-3 py-2">scope</th>
              <th className="px-3 py-2">到期</th>
              <th className="px-3 py-2">状态</th>
              <th className="px-3 py-2 text-right">操作</th>
            </tr>
          </thead>
          <tbody>
            {rules.length === 0 ? (
              <tr>
                <td className="px-3 py-6 text-center text-muted-foreground" colSpan={6}>
                  暂无噪音规则
                </td>
              </tr>
            ) : (
              rules.map((rule) => {
                const left = daysUntil(rule.expires_at)
                const expiring = left <= EXPIRING_DAYS
                return (
                  <tr className="border-t" key={rule.id}>
                    <td className="px-3 py-2">{rule.pattern}</td>
                    <td className="px-3 py-2 font-mono text-xs">{rule.action}</td>
                    <td className="px-3 py-2">{rule.scope}</td>
                    <td className={cn('px-3 py-2', expiring && 'font-medium text-destructive')}>
                      {new Date(rule.expires_at).toLocaleString()}
                      {left <= 0 ? '（已过期）' : `（剩 ${left} 天）`}
                    </td>
                    <td className="px-3 py-2">
                      {rule.effective ? (
                        <Badge tone="success">生效中</Badge>
                      ) : (
                        <Badge tone="danger">已过期</Badge>
                      )}
                    </td>
                    <td className="space-x-2 px-3 py-2 text-right">
                      <Button onClick={() => void handleRenew(rule)} size="sm" variant="outline">
                        续期
                      </Button>
                      <Button onClick={() => void handleDelete(rule)} size="sm" variant="ghost">
                        删除
                      </Button>
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
