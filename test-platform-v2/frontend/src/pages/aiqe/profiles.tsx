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
  approveProfile,
  createProfile,
  listProfiles,
  type ExecutionProfile,
} from '@/api/aiqeConsole'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import ConsoleTabs from './ConsoleTabs'

const PURPOSES = [
  { value: 'core_isolated', label: 'core_isolated（Run 级隔离）' },
  { value: 'integration', label: 'integration（共享命名空间）' },
  { value: 'external_live', label: 'external_live（禁写 fixture）' },
] as const

function errorText(err: unknown): string {
  return err instanceof Error ? err.message : '请求失败'
}

export default function ProfilesPage() {
  useDocumentTitle('Execution Profiles')
  const [profiles, setProfiles] = useState<ExecutionProfile[]>([])
  const [error, setError] = useState('')
  const [name, setName] = useState('')
  const [purpose, setPurpose] = useState<string>('core_isolated')
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    let alive = true
    listProfiles()
      .then((rows) => {
        if (alive) setProfiles(rows)
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
    const trimmed = name.trim()
    if (!trimmed || busy) return
    setBusy(true)
    setError('')
    try {
      const created = await createProfile({ name: trimmed, purpose })
      setProfiles((prev) => [created, ...prev])
      setName('')
    } catch (err: unknown) {
      setError(errorText(err))
    } finally {
      setBusy(false)
    }
  }

  async function handleApprove(profile: ExecutionProfile) {
    setError('')
    try {
      const updated = await approveProfile(profile.id)
      setProfiles((prev) => prev.map((row) => (row.id === updated.id ? updated : row)))
    } catch (err: unknown) {
      setError(errorText(err))
    }
  }

  return (
    <div className="space-y-4 p-6">
      <header className="space-y-3">
        <div>
          <h1 className="text-2xl font-semibold">Execution Profiles</h1>
          <p className="text-sm text-muted-foreground">
            执行配置档：审批通过后 checksum 冻结，只能新建 version。
          </p>
        </div>
        <ConsoleTabs />
      </header>

      {error ? <p className="text-sm text-destructive">{error}</p> : null}

      <Card>
        <CardHeader>
          <CardTitle className="text-base">新建 Profile</CardTitle>
        </CardHeader>
        <CardContent>
          <form className="flex flex-wrap items-end gap-3" onSubmit={handleCreate}>
            <label className="space-y-1 text-sm">
              <span className="text-muted-foreground">名称</span>
              <Input
                aria-label="Profile 名称"
                className="w-56"
                onChange={(event) => setName(event.target.value)}
                placeholder="例如：本地隔离基线"
                value={name}
              />
            </label>
            <label className="space-y-1 text-sm">
              <span className="text-muted-foreground">purpose</span>
              <Select onValueChange={setPurpose} value={purpose}>
                <SelectTrigger aria-label="Profile purpose" className="w-64">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {PURPOSES.map((item) => (
                    <SelectItem key={item.value} value={item.value}>
                      {item.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </label>
            <Button disabled={busy || !name.trim()} type="submit">
              {busy ? '创建中…' : '创建'}
            </Button>
          </form>
        </CardContent>
      </Card>

      <div className="overflow-hidden rounded-lg border">
        <table className="w-full text-sm">
          <thead className="bg-muted/40 text-left">
            <tr>
              <th className="px-3 py-2">名称</th>
              <th className="px-3 py-2">purpose</th>
              <th className="px-3 py-2">version</th>
              <th className="px-3 py-2">审批状态</th>
              <th className="px-3 py-2">checksum</th>
              <th className="px-3 py-2 text-right">操作</th>
            </tr>
          </thead>
          <tbody>
            {profiles.length === 0 ? (
              <tr>
                <td className="px-3 py-6 text-center text-muted-foreground" colSpan={6}>
                  暂无 Profile
                </td>
              </tr>
            ) : (
              profiles.map((profile) => (
                <tr className="border-t" key={profile.id}>
                  <td className="px-3 py-2">{profile.name}</td>
                  <td className="px-3 py-2 font-mono text-xs">{profile.purpose}</td>
                  <td className="px-3 py-2">v{profile.version}</td>
                  <td className="px-3 py-2">
                    {profile.frozen ? (
                      <Badge tone="success">已冻结</Badge>
                    ) : (
                      <Badge tone="warning">待审批</Badge>
                    )}
                  </td>
                  <td className="px-3 py-2 font-mono text-xs" title={profile.checksum}>
                    {profile.checksum.slice(0, 12)}…
                  </td>
                  <td className="px-3 py-2 text-right">
                    <Button
                      disabled={profile.frozen}
                      onClick={() => void handleApprove(profile)}
                      size="sm"
                      variant="outline"
                    >
                      {profile.frozen ? '已审批' : '审批'}
                    </Button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
