import { useState } from 'react'
import { toast } from 'sonner'
import {
  Sheet, SheetContent, SheetDescription, SheetFooter, SheetHeader, SheetTitle,
} from '@/components/ui/sheet'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { acceptWikiDiffItem, rejectWikiDiffItem, createWikiDiffArtifact } from '@/api/wiki'
import type { WikiDiffItem } from '@/types'
import { useAuthStore } from '@/stores/auth'
import { severityBadge } from './wikiSeverity'

interface Props {
  item: WikiDiffItem | null
  onOpenChange: (v: boolean) => void
  onChanged: (item: WikiDiffItem) => void
}

export default function WikiDiffDetailDrawer({ item, onOpenChange, onChanged }: Props) {
  const hasPerm = useAuthStore((s) => s.hasPerm)
  const canDiff = hasPerm('wiki:diff')
  const [busy, setBusy] = useState(false)

  const act = async (fn: () => Promise<any>, msg: string, patch: Partial<WikiDiffItem>) => {
    if (!item) return
    setBusy(true)
    try {
      await fn()
      toast.success(msg)
      onChanged({ ...item, ...patch })
    } catch (e: any) {
      toast.error(e?.message || '操作失败')
    } finally {
      setBusy(false)
    }
  }

  return (
    <Sheet open={!!item} onOpenChange={onOpenChange}>
      <SheetContent className="sm:max-w-[520px] overflow-auto">
        {item && (
          <>
            <SheetHeader>
              <SheetTitle className="flex items-center gap-2 flex-wrap text-left">
                {(() => { const s = severityBadge(item.severity); return (
                  <Badge variant={s.variant} className={s.className}>{item.severity}</Badge>
                ) })()}
                <Badge variant="secondary">{item.dimension}</Badge>
                <Badge variant="outline">{item.diff_type}</Badge>
              </SheetTitle>
              <SheetDescription className="text-left text-foreground font-medium">{item.title}</SheetDescription>
            </SheetHeader>

            <div className="space-y-3 py-4 text-sm">
              <div className="grid grid-cols-2 gap-2">
                <div className="rounded-md border p-2">
                  <div className="text-xs text-muted-foreground mb-1">左侧</div>
                  <div className="break-words whitespace-pre-wrap">{item.left_value || '—'}</div>
                </div>
                <div className="rounded-md border p-2">
                  <div className="text-xs text-muted-foreground mb-1">右侧</div>
                  <div className="break-words whitespace-pre-wrap">{item.right_value || '—'}</div>
                </div>
              </div>
              {item.suggestion && (
                <div className="rounded-md border border-blue-200 bg-blue-50 p-2 text-blue-700 dark:border-blue-800 dark:bg-blue-950/40 dark:text-blue-300">
                  <div className="text-xs font-medium mb-0.5">建议</div>
                  {item.suggestion}
                </div>
              )}
              <div className="text-xs text-muted-foreground">
                证据：<span className="font-mono break-all">{item.evidence_json}</span>
              </div>
              <div className="text-xs">
                处理状态：<Badge variant="outline">{item.review_status}</Badge>
                {item.resolved_artifact_id && (
                  <span className="ml-2 text-muted-foreground">已生成产物 #{item.resolved_artifact_id}</span>
                )}
              </div>
            </div>

            {canDiff && (
              <SheetFooter className="flex-row gap-2 sm:justify-start">
                <Button variant="outline" size="sm" disabled={busy}
                  onClick={() => act(() => rejectWikiDiffItem(item.id), '已忽略', { review_status: 'rejected' })}>
                  忽略
                </Button>
                <Button variant="outline" size="sm" disabled={busy}
                  onClick={() => act(() => acceptWikiDiffItem(item.id), '已确认', { review_status: 'accepted' })}>
                  确认
                </Button>
                <Button size="sm" disabled={busy || !!item.resolved_artifact_id}
                  onClick={() => act(
                    async () => { const r = await createWikiDiffArtifact(item.id); return r },
                    '已生成待审产物', { review_status: 'accepted' })}>
                  生成待审用例
                </Button>
              </SheetFooter>
            )}
          </>
        )}
      </SheetContent>
    </Sheet>
  )
}
