import { useState } from 'react'
import { toast } from 'sonner'
import {
  fetchChannels,
  createChannel,
  updateChannel,
  deleteChannel,
  testNotify,
  type NotificationChannel,
  type ChannelCreate,
  type ChannelUpdate,
} from '@/api/notify'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Switch } from '@/components/ui/switch'
import { Checkbox } from '@/components/ui/checkbox'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import PageHeader from '@/components/PageHeader'
import { AsyncState } from '@/components/state'
import useApi from '@/hooks/useApi'
import {
  Plus,
  Edit,
  Trash2,
  Play,
  Bell,
  Link2,
  Loader2,
} from '@/lib/icons'

// ── Event labels ──
const EVENT_OPTIONS: { value: string; label: string }[] = [
  { value: 'plan_done', label: '计划执行完成' },
  { value: 'defect_assigned', label: '缺陷分配' },
  { value: 'schedule_failed', label: '计划执行失败' },
  { value: 'report_generated', label: '报告生成' },
]

const PROVIDER_OPTIONS: { value: string; label: string }[] = [
  { value: 'feishu', label: '飞书' },
  { value: 'dingtalk', label: '钉钉' },
  { value: 'wecom_work', label: '企业微信' },
  { value: 'generic', label: '通用 Webhook' },
]

// ── Empty form state ──
function emptyForm(): {
  name: string
  channel_type: 'webhook' | 'email'
  provider: string
  webhook_url: string
  enabled: boolean
  events: string[]
} {
  return {
    name: '',
    channel_type: 'webhook',
    provider: 'feishu',
    webhook_url: '',
    enabled: true,
    events: ['plan_done', 'defect_assigned'],
  }
}

export default function NotifyPage() {
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [form, setForm] = useState(emptyForm())
  const [saving, setSaving] = useState(false)
  const [testOpen, setTestOpen] = useState(false)
  const [testing, setTesting] = useState(false)

  const { data, isLoading, isError, error, refetch } = useApi(
    () => fetchChannels(),
    [],
  )

  const channels = data || []

  // ── Form helpers ──
  const setField = <K extends keyof typeof form>(key: K, value: (typeof form)[K]) => {
    setForm((prev) => ({ ...prev, [key]: value }))
  }

  const toggleEvent = (event: string) => {
    setForm((prev) => {
      const next = prev.events.includes(event)
        ? prev.events.filter((e) => e !== event)
        : [...prev.events, event]
      return { ...prev, events: next }
    })
  }

  // ── Actions ──
  const openCreate = () => {
    setEditingId(null)
    setForm(emptyForm())
    setDialogOpen(true)
  }

  const openEdit = (ch: NotificationChannel) => {
    setEditingId(ch.id)
    setForm({
      name: ch.name,
      channel_type: ch.channel_type,
      provider: ch.provider || 'generic',
      webhook_url: ch.webhook_url || '',
      enabled: ch.enabled,
      events: ch.events || [],
    })
    setDialogOpen(true)
  }

  const handleSave = async () => {
    if (!form.name.trim()) {
      toast.error('请输入渠道名称')
      return
    }
    if (form.channel_type === 'webhook' && !form.webhook_url.trim()) {
      toast.error('请输入 Webhook URL')
      return
    }
    if (form.channel_type === 'email' && !form.webhook_url.trim()) {
      toast.error('请输入收件人邮箱')
      return
    }

    setSaving(true)
    try {
      const payload: ChannelCreate | ChannelUpdate = {
        name: form.name.trim(),
        provider: form.channel_type === 'webhook' ? form.provider : undefined,
        webhook_url: form.webhook_url.trim(),
        enabled: form.enabled,
        events: form.events,
      }

      if (editingId) {
        await updateChannel(editingId, payload)
        toast.success('渠道已更新')
      } else {
        await createChannel({ ...payload, channel_type: form.channel_type } as ChannelCreate)
        toast.success('渠道已创建')
      }
      setDialogOpen(false)
      refetch()
    } catch {
      // error toast handled by client interceptor
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async (id: number) => {
    try {
      await deleteChannel(id)
      toast.success('渠道已删除')
      refetch()
    } catch {
      // error toast handled by client interceptor
    }
  }

  const handleTest = async () => {
    setTesting(true)
    try {
      const result = await testNotify()
      toast.success(`测试通知已发送: 成功 ${result.sent}, 失败 ${result.failed}, 跳过 ${result.skipped}`)
      setTestOpen(false)
    } catch {
      // error toast handled by client interceptor
    } finally {
      setTesting(false)
    }
  }

  // ── Render ──
  return (
    <div>
      <PageHeader title="通知配置" description="管理 Webhook 和邮件通知渠道">
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={() => setTestOpen(true)} data-icon="inline-start">
            <Play />
            测试发送
          </Button>
          <Button size="sm" onClick={openCreate} data-icon="inline-start">
            <Plus />
            新增渠道
          </Button>
        </div>
      </PageHeader>

      <div className="mt-6">
        <AsyncState
          isLoading={isLoading}
          isError={isError}
          error={error}
          data={channels.length > 0 ? channels : undefined}
          onRetry={refetch}
          emptyTitle="暂无通知渠道"
          emptyDescription="点击「新增渠道」创建第一个 Webhook 或邮件通知"
          emptyAction={{ label: '新增渠道', onClick: openCreate }}
          loadingVariant="skeleton"
          skeletonType="table"
          loadingRows={3}
        >
          {(items) => (
            <div className="rounded-xl border bg-card">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>渠道名称</TableHead>
                    <TableHead>类型</TableHead>
                    <TableHead>提供商</TableHead>
                    <TableHead>订阅事件</TableHead>
                    <TableHead>状态</TableHead>
                    <TableHead className="w-[160px]">操作</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {items.map((ch) => (
                    <TableRow key={ch.id}>
                      <TableCell className="font-medium">{ch.name}</TableCell>
                      <TableCell>
                        <Badge variant={ch.channel_type === 'webhook' ? 'default' : 'secondary'}>
                          {ch.channel_type === 'webhook' ? 'Webhook' : '邮件'}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {ch.channel_type === 'webhook'
                          ? (PROVIDER_OPTIONS.find((p) => p.value === ch.provider)?.label || ch.provider || '—')
                          : '—'}
                      </TableCell>
                      <TableCell>
                        <div className="flex flex-wrap gap-1">
                          {ch.events && ch.events.length > 0 ? (
                            ch.events.map((ev) => (
                              <Badge key={ev} variant="outline" className="text-xs">
                                {EVENT_OPTIONS.find((e) => e.value === ev)?.label || ev}
                              </Badge>
                            ))
                          ) : (
                            <span className="text-xs text-muted-foreground">无</span>
                          )}
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge variant={ch.enabled ? 'default' : 'secondary'}>
                          {ch.enabled ? '启用' : '禁用'}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-1">
                          <Button size="sm" variant="ghost" onClick={() => openEdit(ch)}>
                            <Edit className="size-4" />
                          </Button>
                          <AlertDialog>
                            <AlertDialogTrigger asChild>
                              <Button size="sm" variant="ghost">
                                <Trash2 className="size-4 text-destructive" />
                              </Button>
                            </AlertDialogTrigger>
                            <AlertDialogContent>
                              <AlertDialogHeader>
                                <AlertDialogTitle>确定删除？</AlertDialogTitle>
                                <AlertDialogDescription>
                                  将删除通知渠道「{ch.name}」，此操作不可撤销。
                                </AlertDialogDescription>
                              </AlertDialogHeader>
                              <AlertDialogFooter>
                                <AlertDialogCancel>取消</AlertDialogCancel>
                                <AlertDialogAction variant="destructive" onClick={() => handleDelete(ch.id)}>
                                  删除
                                </AlertDialogAction>
                              </AlertDialogFooter>
                            </AlertDialogContent>
                          </AlertDialog>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </AsyncState>
      </div>

      {/* ── Create / Edit Dialog ── */}
      <Dialog open={dialogOpen} onOpenChange={(open) => { if (!open) setDialogOpen(false) }}>
        <DialogContent className="sm:max-w-[520px]">
          <DialogHeader>
            <DialogTitle>{editingId ? '编辑渠道' : '新增渠道'}</DialogTitle>
            <DialogDescription>
              {editingId ? '修改通知渠道配置' : '创建新的 Webhook 或邮件通知渠道'}
            </DialogDescription>
          </DialogHeader>

          <div className="flex flex-col gap-4 py-2">
            {/* Channel type */}
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium">渠道类型</label>
              <Select
                value={form.channel_type}
                onValueChange={(v) => setField('channel_type', v as 'webhook' | 'email')}
                disabled={!!editingId}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="webhook">Webhook</SelectItem>
                  <SelectItem value="email">邮件</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Name */}
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium">渠道名称</label>
              <Input
                placeholder="如：飞书通知、邮件告警"
                value={form.name}
                onChange={(e) => setField('name', e.target.value)}
              />
            </div>

            {/* Provider (webhook only) */}
            {form.channel_type === 'webhook' && (
              <div className="flex flex-col gap-1.5">
                <label className="text-sm font-medium">提供商</label>
                <Select
                  value={form.provider}
                  onValueChange={(v) => setField('provider', v)}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {PROVIDER_OPTIONS.map((p) => (
                      <SelectItem key={p.value} value={p.value}>
                        {p.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}

            {/* Webhook URL / Email recipients */}
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium">
                {form.channel_type === 'webhook' ? 'Webhook URL' : '收件人邮箱'}
              </label>
              <Input
                placeholder={
                  form.channel_type === 'webhook'
                    ? 'https://open.feishu.cn/open-apis/bot/v2/hook/xxx'
                    : 'user@example.com, user2@example.com'
                }
                value={form.webhook_url}
                onChange={(e) => setField('webhook_url', e.target.value)}
              />
              {form.channel_type === 'email' && (
                <span className="text-xs text-muted-foreground">多个邮箱用英文逗号分隔</span>
              )}
            </div>

            {/* Events */}
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium">订阅事件</label>
              <div className="grid grid-cols-2 gap-2 rounded-lg border p-3">
                {EVENT_OPTIONS.map((ev) => (
                  <label
                    key={ev.value}
                    className="flex items-center gap-2 text-sm cursor-pointer"
                  >
                    <Checkbox
                      checked={form.events.includes(ev.value)}
                      onCheckedChange={() => toggleEvent(ev.value)}
                    />
                    {ev.label}
                  </label>
                ))}
              </div>
            </div>

            {/* Enabled toggle */}
            <div className="flex items-center justify-between rounded-lg border p-3">
              <div>
                <div className="text-sm font-medium">启用</div>
                <div className="text-xs text-muted-foreground">关闭后暂停发送通知</div>
              </div>
              <Switch
                checked={form.enabled}
                onCheckedChange={(v) => setField('enabled', v)}
              />
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>
              取消
            </Button>
            <Button disabled={saving} onClick={handleSave} data-icon="inline-start">
              {saving && <Loader2 className="animate-spin" />}
              {editingId ? '保存' : '创建'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ── Test Dialog ── */}
      <Dialog open={testOpen} onOpenChange={(open) => { if (!open) setTestOpen(false) }}>
        <DialogContent className="sm:max-w-[400px]">
          <DialogHeader>
            <DialogTitle>测试通知发送</DialogTitle>
            <DialogDescription>
              向所有已启用且订阅了「计划执行完成」事件的渠道发送测试消息。
            </DialogDescription>
          </DialogHeader>

          <div className="py-2 text-sm text-muted-foreground">
            将向项目下所有启用的通知渠道发送一条测试通知，用于验证 Webhook 或邮件配置是否正确。
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setTestOpen(false)}>
              取消
            </Button>
            <Button disabled={testing} onClick={handleTest} data-icon="inline-start">
              {testing && <Loader2 className="animate-spin" />}
              发送测试
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
