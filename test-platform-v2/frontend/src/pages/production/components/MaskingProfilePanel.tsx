import { useState } from 'react'
import { toast } from 'sonner'
import { Badge, Button, Card, CardContent, CardHeader, CardTitle, Input, Label, Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/ui'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { MaskPreviewTable, type MaskEntry } from './MaskPreviewTable'
import type { MaskingProfile, MaskingRule } from '@/api/production'
import { Plus, Trash2, ShieldCheck } from '@/lib/icons'

const STRATEGIES: MaskingRule['strategy'][] = ['REDACT', 'HASH', 'TOKENIZE', 'FAKE', 'PRESERVE']

let ruleSeq = 0
function nextId(): string {
  ruleSeq += 1
  return `rule-${Date.now()}-${ruleSeq}`
}

interface MaskingProfilePanelProps {
  initialProfile?: MaskingProfile | null
  onSave?: (profile: MaskingProfile) => void | Promise<void>
  saving?: boolean
}

/**
 * Compose a masking profile and its redaction rules. Local-state form; the
 * composed profile is handed to `onSave` (backend persistence endpoints for
 * masking profiles are not part of the V36 contract).
 */
export function MaskingProfilePanel({ initialProfile = null, onSave, saving = false }: MaskingProfilePanelProps) {
  const [name, setName] = useState(initialProfile?.name ?? '')
  const [description, setDescription] = useState(initialProfile?.description ?? '')
  const [rules, setRules] = useState<MaskingRule[]>(initialProfile?.rules ?? [])
  const [entityPattern, setEntityPattern] = useState('')
  const [fieldPattern, setFieldPattern] = useState('')
  const [classification, setClassification] = useState('')
  const [strategy, setStrategy] = useState<MaskingRule['strategy']>('REDACT')
  const [priority, setPriority] = useState('10')
  const [savingLocal, setSavingLocal] = useState(false)

  const addRule = () => {
    if (!entityPattern.trim() && !fieldPattern.trim()) {
      toast.error('请填写 entity_pattern 或 field_pattern')
      return
    }
    setRules((prev) => [
      ...prev,
      {
        id: nextId(),
        entity_pattern: entityPattern.trim(),
        field_pattern: fieldPattern.trim(),
        classification: classification.trim() || 'UNKNOWN',
        strategy,
        priority: Number(priority) || 0,
      },
    ])
    setEntityPattern('')
    setFieldPattern('')
    setClassification('')
  }

  const removeRule = (id: string) => {
    setRules((prev) => prev.filter((rule) => rule.id !== id))
  }

  const save = async () => {
    if (!name.trim()) {
      toast.error('请填写脱敏配置名称')
      return
    }
    setSavingLocal(true)
    const profile: MaskingProfile = {
      id: initialProfile?.id ?? nextId(),
      name: name.trim(),
      description: description.trim() || null,
      rules,
    }
    try {
      await onSave?.(profile)
      toast.success('脱敏配置已保存')
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '保存失败')
    } finally {
      setSavingLocal(false)
    }
  }

  const masksAsEntries: MaskEntry[] = rules.map((rule) => ({
    entity: rule.entity_pattern,
    field: rule.field_pattern,
    classification: rule.classification,
    strategy: rule.strategy,
    priority: rule.priority,
  }))

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <ShieldCheck className="size-4" />
            脱敏配置
            <Badge tone="neutral">{rules.length} 条规则</Badge>
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="space-y-1.5">
              <Label>配置名称</Label>
              <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="如 production-masking-v1" />
            </div>
            <div className="space-y-1.5">
              <Label>描述（可选）</Label>
              <Input value={description} onChange={(e) => setDescription(e.target.value)} placeholder="用途说明" />
            </div>
          </div>

          <div className="rounded-lg border bg-muted/20 p-3">
            <p className="mb-2 text-xs font-medium text-muted-foreground">新增脱敏规则</p>
            <div className="grid gap-3 sm:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_minmax(0,1fr)_minmax(0,1fr)_minmax(0,1fr)_auto]">
              <div className="space-y-1.5">
                <Label>实体匹配</Label>
                <Input value={entityPattern} onChange={(e) => setEntityPattern(e.target.value)} placeholder="entity_pattern" />
              </div>
              <div className="space-y-1.5">
                <Label>字段匹配</Label>
                <Input value={fieldPattern} onChange={(e) => setFieldPattern(e.target.value)} placeholder="field_pattern" />
              </div>
              <div className="space-y-1.5">
                <Label>分类</Label>
                <Input value={classification} onChange={(e) => setClassification(e.target.value)} placeholder="classification" />
              </div>
              <div className="space-y-1.5">
                <Label>策略</Label>
                <Select value={strategy} onValueChange={(v) => setStrategy(v as MaskingRule['strategy'])}>
                  <SelectTrigger>
                    <SelectValue placeholder="选择策略" />
                  </SelectTrigger>
                  <SelectContent>
                    {STRATEGIES.map((s) => (
                      <SelectItem key={s} value={s}>{s}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1.5">
                <Label>优先级</Label>
                <Input value={priority} onChange={(e) => setPriority(e.target.value)} inputMode="numeric" />
              </div>
              <div className="flex items-end">
                <Button variant="secondary" size="sm" onClick={addRule}>
                  <Plus className="size-3.5" /> 添加
                </Button>
              </div>
            </div>
          </div>

          {rules.length > 0 ? (
            <div className="overflow-hidden rounded-lg border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>实体</TableHead>
                    <TableHead>字段</TableHead>
                    <TableHead>分类</TableHead>
                    <TableHead>策略</TableHead>
                    <TableHead>优先级</TableHead>
                    <TableHead className="w-10" />
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {rules.map((rule) => (
                    <TableRow key={rule.id}>
                      <TableCell className="max-w-[22ch] truncate font-mono text-xs">{rule.entity_pattern}</TableCell>
                      <TableCell className="max-w-[22ch] truncate font-mono text-xs">{rule.field_pattern}</TableCell>
                      <TableCell className="max-w-[22ch] truncate text-muted-foreground">{rule.classification}</TableCell>
                      <TableCell>
                        <Badge tone="neutral" className={STRATEGY_TONE(rule.strategy)}>{rule.strategy}</Badge>
                      </TableCell>
                      <TableCell className="font-mono">#{rule.priority}</TableCell>
                      <TableCell>
                        <Button variant="ghost" size="icon-sm" aria-label="删除规则" onClick={() => removeRule(rule.id)}>
                          <Trash2 className="size-3.5" />
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">尚未定义规则。</p>
          )}

          <div className="flex items-center gap-2">
            <Button variant="primary" size="sm" onClick={() => void save()} disabled={saving || savingLocal}>
              <ShieldCheck className="size-3.5" /> {savingLocal ? '保存中…' : '保存配置'}
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>脱敏规则预览（Mask Preview）</CardTitle>
        </CardHeader>
        <CardContent>
          <MaskPreviewTable masks={masksAsEntries} />
        </CardContent>
      </Card>
    </div>
  )
}

function STRATEGY_TONE(strategy: string): string {
  return {
    REDACT: 'bg-status-danger-muted text-status-danger',
    HASH: 'bg-status-warning-muted text-status-warning',
    TOKENIZE: 'bg-status-info-muted text-status-info',
    FAKE: 'bg-status-info-muted text-status-info',
    PRESERVE: 'bg-status-success-muted text-status-success',
  }[strategy] ?? 'bg-muted text-muted-foreground'
}
