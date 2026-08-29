import { useState } from 'react'
import { Badge, Button } from '@/ui'
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
  CardAction,
} from '@/components/ui/card'
import { Switch } from '@/components/ui/switch'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import { Save, FileText } from '@/lib/icons'
import { ConstraintEditor } from './ConstraintEditor'
import type { DataRequirement, UpdateDataRequirementInput } from '@/api/dataRequirements'

export interface DataRequirementCardProps {
  requirement: DataRequirement
  onUpdate: (id: number, patch: UpdateDataRequirementInput) => Promise<void> | void
  /** Currently persisting this card's latest edit. */
  saving?: boolean
}

const SHARING_POLICIES = [
  'read_only',
  'read_write',
  'segregated',
  'shared',
  'private',
]

const CLEANUP_POLICIES = [
  'post_run',
  'ttl_based',
  'on_release',
  'manual',
  'none',
]

export function DataRequirementCard({ requirement, onUpdate, saving }: DataRequirementCardProps) {
  const [editEntityType, setEditEntityType] = useState(false)
  const [entityDraft, setEntityDraft] = useState<string | null>(null)
  const [savingField, setSavingField] = useState<string | null>(null)

  const patch = async (field: string, value: UpdateDataRequirementInput) => {
    setSavingField(field)
    try {
      await onUpdate(requirement.id, value)
    } finally {
      setSavingField(null)
    }
  }

  const commitEntityType = async () => {
    if (entityDraft == null) return
    await patch('entity_type', { entity_type: entityDraft })
    setEditEntityType(false)
  }

  const busy = saving || savingField != null

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <span className="font-mono text-xs">
            {requirement.requirement_key}
          </span>
          {requirement.required && (
            <Badge tone="info">必需</Badge>
          )}
        </CardTitle>
        <CardDescription className="font-mono text-xs">
          #{requirement.id} · 版本 {requirement.scenario_version_id}
        </CardDescription>
        <CardAction>
          <span className="flex items-center gap-1 text-xs text-muted-foreground">
            <FileText className="size-3.5" />
            {editEntityType ? '编辑业务实体' : '业务实体'}
          </span>
        </CardAction>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Business entity type */}
        <div className="space-y-1.5">
          <span className="text-xs font-medium text-muted-foreground">业务实体 (entity_type)</span>
          {editEntityType ? (
            <div className="flex gap-1">
              <Textarea
                value={entityDraft ?? ''}
                onChange={(e) => setEntityDraft(e.target.value)}
                rows={1}
                className="font-mono text-xs"
                autoFocus
              />
              <Button
                variant="secondary"
                size="icon-sm"
                aria-label="保存实体类型"
                disabled={busy}
                onClick={commitEntityType}
              >
                <Save className="size-3.5" />
              </Button>
            </div>
          ) : (
            <div
              className="cursor-pointer rounded-md border px-2 py-1.5 font-mono text-xs"
              role="button"
              tabIndex={0}
              onClick={() => { setEntityDraft(requirement.entity_type); setEditEntityType(true) }}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault()
                  setEntityDraft(requirement.entity_type)
                  setEditEntityType(true)
                }
              }}
            >
              {requirement.entity_type || <span className="text-muted-foreground">未设置</span>}
            </div>
          )}
        </div>

        {/* Constraints */}
        <ConstraintEditor
          constraints={requirement.constraints_json}
          onChange={(next) => void patch('constraints', { constraints: next ?? undefined })}
        />

        {/* Required toggle */}
        <div className="flex items-center justify-between rounded-md border px-2 py-1.5">
          <div className="flex items-center gap-2 text-sm">
            <span className="font-medium">必需 (required)</span>
            {requirement.required && <Badge variant="outline">必选</Badge>}
          </div>
          <Switch
            checked={requirement.required}
            disabled={busy}
            onCheckedChange={(v) => void patch('required', { required: v })}
            aria-label="切换是否必需"
          />
        </div>

        {/* Sharing policy */}
        <div className="space-y-1.5">
          <span className="text-xs font-medium text-muted-foreground">共享策略 (sharing_policy)</span>
          <Select
            value={requirement.sharing_policy ?? ''}
            disabled={busy}
            onValueChange={(v) => void patch('sharing_policy', { sharing_policy: v || undefined })}
          >
            <SelectTrigger className="w-full">
              <SelectValue placeholder="选择一个共享策略" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="">未设置</SelectItem>
              {SHARING_POLICIES.map((p) => (
                <SelectItem key={p} value={p}>{p}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Cleanup policy */}
        <div className="space-y-1.5">
          <span className="text-xs font-medium text-muted-foreground">清理策略 (cleanup_policy)</span>
          <Select
            value={requirement.cleanup_policy ?? ''}
            disabled={busy}
            onValueChange={(v) => void patch('cleanup_policy', { cleanup_policy: v || undefined })}
          >
            <SelectTrigger className="w-full">
              <SelectValue placeholder="选择一个清理策略" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="">未设置</SelectItem>
              {CLEANUP_POLICIES.map((p) => (
                <SelectItem key={p} value={p}>{p}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </CardContent>
    </Card>
  )
}
