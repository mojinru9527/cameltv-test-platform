import { useState } from 'react'
import { toast } from 'sonner'
import { Badge, Button, Input } from '@/ui'
import { Checkbox } from '@/components/ui/checkbox'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import { Edit, Import, Loader2 } from '@/lib/icons'
import type { AIGeneratedCase } from '@/types'
import { ClientScopeBadges, PRIORITY_CLASSES, renderSteps } from './AiDisplayParts'

interface Props {
  funcCases: AIGeneratedCase[]
  selectedKeys: number[]
  editingIndex: number | null
  importing: boolean
  createPlan: boolean
  getDisplayCase: (c: AIGeneratedCase) => AIGeneratedCase
  isCaseEdited: (c: AIGeneratedCase) => boolean
  onToggleAll: () => void
  onToggleOne: (index: number) => void
  onStartEdit: (c: AIGeneratedCase) => void
  onSaveEdit: (updated: AIGeneratedCase) => Promise<boolean>
  onCancelEdit: () => void
  onCreatePlanChange: (checked: boolean) => void
  onImport: (indices: number[]) => void
}

// ── Inline edit form for functional cases (no API fields) ──

function InlineEditRow({
  initial,
  onSave,
  onCancel,
}: {
  initial: AIGeneratedCase
  onSave: (updated: AIGeneratedCase) => Promise<boolean>
  onCancel: () => void
}) {
  const [title, setTitle] = useState(initial.title || '')
  const [priority, setPriority] = useState(initial.priority || 'P2')
  const [module, setModule] = useState(initial.module || '')
  const [preconditions, setPreconditions] = useState(initial.preconditions || '')
  const [steps, setSteps] = useState(() => {
    try { return JSON.stringify(JSON.parse(initial.steps), null, 2) } catch { return initial.steps || '' }
  })
  const [expectedResult, setExpectedResult] = useState(initial.expected_result || '')
  const [remark, setRemark] = useState(initial.remark || '')
  const [saving, setSaving] = useState(false)

  const handleSave = async () => {
    const t = title.trim()
    if (!t) { toast.warning('请输入用例标题'); return }
    let s = steps.trim()
    if (s) { try { JSON.parse(s) } catch { toast.warning('步骤需为有效 JSON 格式'); return } }
    setSaving(true)
    try {
      await onSave({
        ...initial,
        title: t,
        priority,
        module: module.trim(),
        preconditions: preconditions.trim(),
        steps: s,
        expected_result: expectedResult.trim(),
        remark: remark.trim(),
      })
    } finally {
      setSaving(false)
    }
  }

  return (
    <TableRow className="bg-status-warning-muted border-status-warning-border">
      <TableCell colSpan={9} className="p-0">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 p-4">
          <div className="sm:col-span-2 lg:col-span-3">
            <label className="mb-1 block text-xs font-medium">用例标题 *</label>
            <Input placeholder="用例标题" value={title} onChange={(e) => setTitle(e.target.value)} />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium">重要程度</label>
            <Select value={priority} onValueChange={setPriority}>
              <SelectTrigger size="sm"><SelectValue /></SelectTrigger>
              <SelectContent>
                {['P0', 'P1', 'P2', 'P3'].map((p) => <SelectItem key={p} value={p}>{p}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium">所属模块</label>
            <Input placeholder="模块名" value={module} onChange={(e) => setModule(e.target.value)} />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium">备注</label>
            <Input placeholder="备注信息" value={remark} onChange={(e) => setRemark(e.target.value)} />
          </div>
          <div className="sm:col-span-2 lg:col-span-3">
            <label className="mb-1 block text-xs font-medium">前置条件</label>
            <Textarea rows={2} placeholder="执行用例前需要满足的条件" value={preconditions} onChange={(e) => setPreconditions(e.target.value)} />
          </div>
          <div className="sm:col-span-2 lg:col-span-3">
            <label className="mb-1 block text-xs font-medium">测试步骤 (JSON)</label>
            <Textarea
              rows={4}
              placeholder='[{"desc":"操作描述","expected":"预期结果"}]'
              value={steps}
              onChange={(e) => setSteps(e.target.value)}
              className="font-mono text-xs"
            />
          </div>
          <div className="sm:col-span-2 lg:col-span-3">
            <label className="mb-1 block text-xs font-medium">预期结果</label>
            <Textarea rows={2} placeholder="整体预期结果描述" value={expectedResult} onChange={(e) => setExpectedResult(e.target.value)} />
          </div>
          <div className="sm:col-span-2 lg:col-span-3 flex items-center gap-2 pt-1">
            <Button size="sm" onClick={handleSave} disabled={saving}>
              {saving && <Loader2 className="size-3.5 animate-spin" />}
              保存
            </Button>
            <Button size="sm" variant="secondary" onClick={onCancel} disabled={saving}>取消</Button>
          </div>
        </div>
      </TableCell>
    </TableRow>
  )
}

export default function AiFuncCasesPanel({
  funcCases,
  selectedKeys,
  editingIndex,
  importing,
  createPlan,
  getDisplayCase,
  isCaseEdited,
  onToggleAll,
  onToggleOne,
  onStartEdit,
  onSaveEdit,
  onCancelEdit,
  onCreatePlanChange,
  onImport,
}: Props) {
  return (
    <>
      <div className="max-h-[55vh] overflow-auto border rounded-lg">
        <Table className="min-w-[1200px]">
          <TableHeader>
            <TableRow>
              <TableHead className="w-10">
                <Checkbox
                  checked={selectedKeys.length === funcCases.length && funcCases.length > 0}
                  onCheckedChange={onToggleAll}
                />
              </TableHead>
              <TableHead className="w-[210px]">用例标题</TableHead>
              <TableHead className="w-[80px] text-center">重要程度</TableHead>
              <TableHead className="w-[110px]">模块</TableHead>
              <TableHead className="w-[70px] text-center">适用端</TableHead>
              <TableHead className="w-[150px]">前提条件</TableHead>
              <TableHead className="w-[240px]">操作步骤</TableHead>
              <TableHead className="w-[210px]">预期结果</TableHead>
              <TableHead className="w-[110px]">备注</TableHead>
              <TableHead className="w-[60px] text-center">操作</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {funcCases.map((c) => {
              const display = getDisplayCase(c)
              const edited = isCaseEdited(c)
              const isEditing = editingIndex === c.index

              if (isEditing) {
                return (
                  <InlineEditRow
                    key={c.index}
                    initial={display}
                    onSave={onSaveEdit}
                    onCancel={onCancelEdit}
                  />
                )
              }

              return (
                <TableRow key={c.index} className={edited ? 'bg-status-warning-muted' : undefined}>
                  <TableCell>
                    <Checkbox
                      checked={selectedKeys.includes(c.index)}
                      onCheckedChange={() => onToggleOne(c.index)}
                    />
                  </TableCell>
                  <TableCell className="font-medium align-top whitespace-normal">
                    <div className="break-words max-w-[200px]">
                      {edited && <span className="text-status-warning mr-1" title="已修改">*</span>}
                      {display.title}
                      {display.imported && (
                        <Badge tone="neutral" className="ml-1.5 border-status-success-border bg-status-success-muted text-status-success text-xs leading-[16px]">
                          已导入
                        </Badge>
                      )}
                    </div>
                  </TableCell>
                  <TableCell className="text-center">
                    <Badge tone="neutral" className={PRIORITY_CLASSES[display.priority] || 'border-border bg-muted text-muted-foreground'}>
                      {display.priority}
                    </Badge>
                  </TableCell>
                  <TableCell className="break-words max-w-[100px] text-xs align-top whitespace-normal">{display.module || '-'}</TableCell>
                  <TableCell className="text-center align-top">
                    <ClientScopeBadges clients={display.client_scope || []} />
                  </TableCell>
                  <TableCell className="break-words max-w-[140px] text-xs align-top whitespace-normal">{display.preconditions || '-'}</TableCell>
                  <TableCell className="whitespace-normal">{renderSteps(display.steps)}</TableCell>
                  <TableCell className="break-words max-w-[200px] text-xs align-top whitespace-normal">{display.expected_result || '-'}</TableCell>
                  <TableCell className="break-words max-w-[100px] text-xs text-muted-foreground align-top whitespace-normal">{display.remark || '-'}</TableCell>
                  <TableCell className="text-center">
                    <Button
                      variant="ghost"
                      size="icon-sm"
                      aria-label={edited ? '再次编辑用例' : '编辑用例'}
                      onClick={() => onStartEdit(c)}
                    >
                      <Edit className="size-3.5" />
                    </Button>
                  </TableCell>
                </TableRow>
              )
            })}
          </TableBody>
        </Table>
      </div>
      <div className="flex items-center justify-between mt-3">
        <div className="flex items-center gap-3">
          <span className="text-xs text-muted-foreground">
            已选 {selectedKeys.length}/{funcCases.length} 条
            {funcCases.filter((c) => c.imported).length > 0 && (
              <span className="text-status-success ml-2">
                · 已导入 {funcCases.filter((c) => c.imported).length} 条
              </span>
            )}
          </span>
          <label className="flex items-center gap-1.5 text-xs text-muted-foreground cursor-pointer select-none">
            <Checkbox
              checked={createPlan}
              onCheckedChange={(v) => onCreatePlanChange(!!v)}
              className="size-3.5"
            />
            同时创建测试计划
          </label>
        </div>
        <Button
          size="sm"
          onClick={() => onImport(selectedKeys)}
          disabled={importing || selectedKeys.length === 0}
        >
          {importing ? <Loader2 className="size-3.5 animate-spin" /> : <Import className="size-3.5" />}
          导入功能用例 ({selectedKeys.length})
        </Button>
      </div>
    </>
  )
}
