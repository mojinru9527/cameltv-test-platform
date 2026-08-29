import { useEffect, useState } from 'react'
import { Button, Input, Textarea } from '@/ui'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Plus, Trash2, Code2, List, ArrowUp, ArrowDown } from '@/lib/icons'
import { COMMAND_DRIVER_LABELS, type CommandIR, type CommandIRCommand } from '@/api/actionPlans'
import { cn } from '@/lib/utils'

/** Local-draft JSON textarea that commits a valid object on blur (no snap-back). */
function CommandInputField({
  value,
  onCommit,
  label,
}: {
  value: Record<string, unknown>
  onCommit: (value: Record<string, unknown>) => void
  label: string
}) {
  const [draft, setDraft] = useState(JSON.stringify(value ?? {}, null, 2))
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setDraft(JSON.stringify(value ?? {}, null, 2))
  }, [value])

  const commit = () => {
    try {
      const parsed = JSON.parse(draft)
      onCommit(parsed)
      setError(null)
    } catch {
      setError('JSON 不合法')
    }
  }

  return (
    <div className="space-y-1">
      <span className="text-xs text-muted-foreground">{label}</span>
      <Textarea
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        onBlur={commit}
        rows={3}
        className="font-mono text-[11px]"
      />
      {error && <p className="text-xs text-destructive">{error}</p>}
    </div>
  )
}

export interface ActionPlanEditorProps {
  value: CommandIR
  onChange: (value: CommandIR) => void
}

const DRIVERS = ['browser', 'data', 'api', 'assertion']

function nextId(): string {
  return `cmd-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`
}

/**
 * Edit a Command IR. Provides a structured command list (driver / action / input)
 * and a raw JSON view; both stay in sync through the controlled `onChange`.
 * Defaults to showing the business-level Command IR, never hiding commands.
 */
export function ActionPlanEditor({ value, onChange }: ActionPlanEditorProps) {
  const [view, setView] = useState<'structured' | 'json'>('structured')
  const [jsonDraft, setJsonDraft] = useState(JSON.stringify(value, null, 2))
  const [jsonError, setJsonError] = useState<string | null>(null)

  useEffect(() => {
    setJsonDraft(JSON.stringify(value, null, 2))
  }, [value])

  const updateCommand = (id: string, patch: Partial<CommandIRCommand>) => {
    onChange({
      ...value,
      commands: value.commands.map((cmd) => (cmd.id === id ? { ...cmd, ...patch } : cmd)),
    })
  }

  const addCommand = () => {
    onChange({
      ...value,
      commands: [
        ...value.commands,
        { id: nextId(), driver: 'browser', action: 'goto', input: {} },
      ],
    })
  }

  const removeCommand = (id: string) => {
    onChange({ ...value, commands: value.commands.filter((cmd) => cmd.id !== id) })
  }

  const moveCommand = (index: number, delta: -1 | 1) => {
    const target = index + delta
    if (target < 0 || target >= value.commands.length) return
    const next = value.commands.slice()
    const [item] = next.splice(index, 1)
    next.splice(target, 0, item)
    onChange({ ...value, commands: next })
  }

  const applyJson = (draft: string) => {
    setJsonDraft(draft)
    if (draft.trim() === '') return
    try {
      const parsed = JSON.parse(draft) as CommandIR
      if (!parsed || typeof parsed !== 'object' || !Array.isArray(parsed.commands)) {
        setJsonError('JSON 需包含 { schema_version, commands: [] } 形状')
        return
      }
      setJsonError(null)
      onChange(parsed)
    } catch {
      setJsonError('JSON 格式不合法')
    }
  }

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="text-xs font-medium text-muted-foreground">schema_version</span>
          <Input
            value={value.schema_version}
            onChange={(e) => onChange({ ...value, schema_version: e.target.value })}
            className="h-8 w-28 font-mono text-xs"
          />
        </div>
        <div className="flex gap-1 rounded-lg border p-1">
          <button
            type="button"
            onClick={() => setView('structured')}
            className={cn(
              'flex items-center gap-1 rounded-md px-2 py-1 text-xs font-medium',
              view === 'structured' ? 'bg-foreground text-background' : 'text-muted-foreground hover:text-foreground',
            )}
          >
            <List className="size-3.5" /> 结构化
          </button>
          <button
            type="button"
            onClick={() => setView('json')}
            className={cn(
              'flex items-center gap-1 rounded-md px-2 py-1 text-xs font-medium',
              view === 'json' ? 'bg-foreground text-background' : 'text-muted-foreground hover:text-foreground',
            )}
          >
            <Code2 className="size-3.5" /> JSON
          </button>
        </div>
      </div>

      {view === 'json' ? (
        <div className="space-y-1">
          <Textarea
            value={jsonDraft}
            onChange={(e) => applyJson(e.target.value)}
            rows={16}
            className="font-mono text-xs leading-relaxed"
            aria-label="Command IR JSON"
          />
          {jsonError && <p className="text-xs text-destructive">{jsonError}</p>}
          <p className="text-xs text-muted-foreground">粘贴完整 Command IR，保存前请确保 JSON 合法。</p>
        </div>
      ) : (
        <div className="space-y-2">
          {value.commands.length === 0 && (
            <p className="rounded-md border border-dashed px-3 py-4 text-center text-sm text-muted-foreground">
              暂无命令，点击「添加命令」。
            </p>
          )}
          {value.commands.map((cmd, index) => (
            <div key={cmd.id} className="space-y-2 rounded-md border px-3 py-2">
              <div className="flex items-center gap-2">
                <span className="font-mono text-xs text-muted-foreground">#{index + 1}</span>
                <Input
                  value={cmd.id}
                  onChange={(e) => updateCommand(cmd.id, { id: e.target.value })}
                  className="h-8 w-40 font-mono text-xs"
                  aria-label="命令 ID"
                />
                <Select value={cmd.driver} onValueChange={(v) => updateCommand(cmd.id, { driver: v })}>
                  <SelectTrigger className="h-8 w-32">
                    <SelectValue placeholder="driver" />
                  </SelectTrigger>
                  <SelectContent>
                    {DRIVERS.map((d) => (
                      <SelectItem key={d} value={d}>{COMMAND_DRIVER_LABELS[d] ?? d}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Input
                  value={cmd.action}
                  onChange={(e) => updateCommand(cmd.id, { action: e.target.value })}
                  className="h-8 flex-1 font-mono text-xs"
                  placeholder="action"
                  aria-label="动作"
                />
                <div className="flex items-center gap-0.5">
                  <Button variant="ghost" size="icon-sm" disabled={index === 0} onClick={() => moveCommand(index, -1)} aria-label="上移">
                    <ArrowUp className="size-3.5" />
                  </Button>
                  <Button variant="ghost" size="icon-sm" disabled={index === value.commands.length - 1} onClick={() => moveCommand(index, 1)} aria-label="下移">
                    <ArrowDown className="size-3.5" />
                  </Button>
                  <Button variant="ghost" size="icon-sm" onClick={() => removeCommand(cmd.id)} aria-label="删除命令">
                    <Trash2 className="size-3.5" />
                  </Button>
                </div>
              </div>
              <div className="grid gap-2 sm:grid-cols-2">
                <CommandInputField
                  value={cmd.input ?? {}}
                  onCommit={(v) => updateCommand(cmd.id, { input: v })}
                  label="input (JSON)"
                />
                <div className="space-y-1">
                  <span className="text-xs text-muted-foreground">observation_ref（可选）</span>
                  <Textarea
                    value={cmd.observation_ref ?? ''}
                    onChange={(e) => updateCommand(cmd.id, { observation_ref: e.target.value || undefined })}
                    rows={3}
                    className="font-mono text-[11px]"
                  />
                </div>
              </div>
            </div>
          ))}
          <Button variant="secondary" onClick={addCommand}>
            <Plus className="size-4" /> 添加命令
          </Button>
        </div>
      )}
    </div>
  )
}
