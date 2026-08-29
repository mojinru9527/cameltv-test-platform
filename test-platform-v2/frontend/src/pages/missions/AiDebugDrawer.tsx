import { useEffect, useState } from 'react'
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet'
import { Badge, Skeleton } from '@/ui'
import { useAuthStore } from '@/stores/auth'
import {
  fetchAiOperations,
  AI_OPERATION_STATUS_LABELS,
  type AiOperation,
} from '@/api/aiOperations'

/** V30-085 权限点：无权限时不渲染任何调试信息。 */
export const AI_VIEW_DEBUG_PERMISSION = 'mission:ai_view_debug'

const STATUS_COLOR: Record<string, string> = {
  QUEUED: 'bg-muted text-muted-foreground',
  RUNNING: 'bg-status-info-muted text-status-info',
  SUCCEEDED: 'bg-status-success-muted text-status-success',
  FAILED: 'bg-status-danger-muted text-status-danger',
  CANCELLED: 'bg-muted text-muted-foreground',
}

/**
 * 从 token_usage_json 提取可展示的 token 用量。
 * 容忍任意形状：仅展示 number 型字段，缺失时返回 null（显示「—」）。
 */
export function parseTokenUsage(raw: string): { label: string; value: number }[] {
  try {
    const obj = JSON.parse(raw) as Record<string, unknown>
    if (!obj || typeof obj !== 'object') return []
    return Object.entries(obj)
      .filter(([, v]) => typeof v === 'number')
      .map(([k, v]) => ({ label: k, value: v as number }))
  } catch {
    return []
  }
}

/**
 * V30-085 AI Debug Drawer。
 *
 * 仅展示 model / prompt version / status / duration / token（任务卡枚举的五要素）。
 * 明确不渲染 error_message / result_ref_json / prompt 原文——服务层本就不存储
 * secret 与 hidden chain-of-thought，前端同样不展示任何推理过程。
 */
export function AiDebugDrawer({
  missionId,
  open,
  onOpenChange,
}: {
  missionId: number
  open: boolean
  onOpenChange: (open: boolean) => void
}) {
  const permissions = useAuthStore((s) => s.permissions)
  const allowed =
    permissions.includes('*') || permissions.includes(AI_VIEW_DEBUG_PERMISSION)

  const [items, setItems] = useState<AiOperation[]>([])
  const [loading, setLoading] = useState(false)
  const [loaded, setLoaded] = useState(false)

  useEffect(() => {
    if (!open || !allowed || !missionId) return
    const controller = new AbortController()
    setLoading(true)
    fetchAiOperations(missionId, controller.signal)
      .then((rows) => {
        setItems(rows)
        setLoaded(true)
      })
      .catch(() => {
        // 错误已由 aitdeV2 拦截器统一 toast；抽屉内保持空态即可
        setLoaded(true)
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false)
      })
    return () => controller.abort()
  }, [open, allowed, missionId])

  if (!allowed) return null

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="w-full overflow-y-auto sm:max-w-md">
        <SheetHeader>
          <SheetTitle>AI 调试信息</SheetTitle>
          <SheetDescription>
            仅展示模型、Prompt 版本、状态、耗时与 Token 用量；不包含任何推理过程或密钥。
          </SheetDescription>
        </SheetHeader>
        <div className="space-y-2 px-4 pb-6" aria-busy={loading}>
          {loading ? (
            <div role="status" aria-label="加载中" className="space-y-2">
              {Array.from({ length: 3 }).map((_, i) => (
                <Skeleton key={i} className="h-20 w-full" />
              ))}
            </div>
          ) : items.length === 0 ? (
            <p className="py-8 text-center text-sm text-muted-foreground" role="status">
              {loaded ? '暂无 AI 操作记录。' : '加载失败。'}
            </p>
          ) : (
            items.map((op) => (
              <div key={op.id} className="rounded-lg border p-3 text-sm">
                <div className="flex items-center justify-between gap-2">
                  <span className="font-medium">{op.operation_type || 'AI 操作'}</span>
                  <Badge
                    variant="secondary"
                    className={STATUS_COLOR[op.status] ?? 'bg-muted text-muted-foreground'}
                  >
                    {AI_OPERATION_STATUS_LABELS[op.status] ?? op.status}
                  </Badge>
                </div>
                <dl className="mt-2 grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-xs text-muted-foreground">
                  <dt>模型</dt>
                  <dd className="truncate">
                    {[op.model_provider, op.model_name].filter(Boolean).join('/') || '—'}
                  </dd>
                  <dt>Prompt 版本</dt>
                  <dd className="truncate font-mono">{op.prompt_version || '—'}</dd>
                  <dt>耗时</dt>
                  <dd>{op.duration_ms != null ? `${op.duration_ms} ms` : '—'}</dd>
                  <dt>Token</dt>
                  <dd>
                    {parseTokenUsage(op.token_usage_json)
                      .map((t) => `${t.label}=${t.value}`)
                      .join(', ') || '—'}
                  </dd>
                </dl>
              </div>
            ))
          )}
        </div>
      </SheetContent>
    </Sheet>
  )
}
