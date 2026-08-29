import { useState } from 'react'
import { Button } from '@/ui'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { cn } from '@/lib/utils'
import { Plus, Trash2, Check, Code2, KeyRound } from '@/lib/icons'

/**
 * Edits a data-requirement `constraints_json` object as key/value rows (default)
 * or as raw JSON text. Never renders SQL — constraints are purely business
 * key/value pairs on top of `entity_type`.
 */
export interface ConstraintEditorProps {
  constraints: Record<string, unknown> | null
  onChange: (value: Record<string, unknown> | null) => void
  className?: string
  /** Optional human label for the group; defaults to "约束 (constraints)". */
  label?: string
}

function valueToText(value: unknown): string {
  if (value == null) return ''
  if (typeof value === 'string') return value
  return JSON.stringify(value)
}

function textToValue(text: string): unknown {
  const trimmed = text.trim()
  if (trimmed === '') return null
  try {
    return JSON.parse(trimmed)
  } catch {
    return trimmed
  }
}

export function ConstraintEditor({ constraints, onChange, className, label = '约束 (constraints)' }: ConstraintEditorProps) {
  const [mode, setMode] = useState<'rows' | 'json'>('rows')
  const [jsonText, setJsonText] = useState<string>('')
  const [jsonError, setJsonError] = useState<string | null>(null)

  const rows = constraints ? Object.entries(constraints) : []
  const hasConstr = constraints != null && Object.keys(constraints).length > 0

  const switchToJson = () => {
    setJsonText(constraints ? JSON.stringify(constraints, null, 2) : '{}')
    setJsonError(null)
    setMode('json')
  }

  const applyJson = () => {
    try {
      const parsed = JSON.parse(jsonText) as Record<string, unknown>
      onChange(parsed)
      setJsonError(null)
    } catch (err) {
      setJsonError(err instanceof Error ? err.message : 'JSON 格式错误')
    }
  }

  const setRowValue = (key: string, value: unknown) => {
    onChange({ ...(constraints ?? {}), [key]: value })
  }

  const removeRow = (key: string) => {
    const next = { ...(constraints ?? {}) }
    delete next[key]
    onChange(Object.keys(next).length > 0 ? next : null)
  }

  const addRow = () => {
    const key = `constraint_${rows.length + 1}`
    onChange({ ...(constraints ?? {}), [key]: '' })
  }

  if (mode === 'json') {
    return (
      <div className={cn('space-y-2', className)}>
        <div className="flex items-center justify-between">
          <span className="text-xs font-medium text-muted-foreground">{label}</span>
          <div className="flex gap-1">
            <Button variant="ghost" size="xs" onClick={() => setMode('rows')}>
              <KeyRound className="size-3.5" /> 键值视图
            </Button>
            <Button variant="secondary" size="xs" onClick={applyJson} disabled={Boolean(jsonError)}>
              <Check className="size-3.5" /> 应用
            </Button>
          </div>
        </div>
        <Textarea
          value={jsonText}
          onChange={(e) => {
            setJsonText(e.target.value)
            setJsonError(null)
          }}
          rows={6}
          spellCheck={false}
          className="font-mono text-xs"
          placeholder="{ &quot;field&quot;: &quot;value&quot; }"
        />
        {jsonError && <p className="text-xs text-destructive">{jsonError}</p>}
      </div>
    )
  }

  return (
    <div className={cn('space-y-2', className)}>
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium text-muted-foreground">{label}</span>
        <div className="flex gap-1">
          <Button variant="ghost" size="xs" onClick={addRow}>
            <Plus className="size-3.5" /> 添加项
          </Button>
          <Button variant="ghost" size="xs" onClick={switchToJson}>
            <Code2 className="size-3.5" /> JSON
          </Button>
        </div>
      </div>
      {!hasConstr ? (
        <p className="rounded-md border border-dashed px-3 py-2 text-xs text-muted-foreground">
          无约束。可点击「添加项」或切换到 JSON 编辑。
        </p>
      ) : (
        <div className="divide-y rounded-md border">
          {rows.map(([key, value]) => (
            <div key={key} className="grid grid-cols-[1fr_1fr_auto] items-center gap-2 px-2 py-1.5">
              <Input
                value={key}
                className="h-7 font-mono text-xs"
                aria-label={`约束键 ${key}`}
                readOnly
              />
              <Input
                defaultValue={valueToText(value)}
                key={`${key}:${valueToText(value)}`}
                className="h-7 font-mono text-xs"
                aria-label={`约束值 ${key}`}
                onBlur={(e) => setRowValue(key, textToValue(e.target.value))}
              />
              <Button
                variant="ghost"
                size="icon-xs"
                aria-label={`删除约束 ${key}`}
                onClick={() => removeRow(key)}
              >
                <Trash2 className="size-3.5" />
              </Button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
