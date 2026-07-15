import { useMemo, useState } from 'react'
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

/** severity display name mapping for tooltips */
const SEVERITY_LABEL: Record<string, string> = {
  P0: '阻断 (critical)',
  P1: '高 (high)',
  P2: '中 (medium)',
  P3: '低 (low)',
}

/** Parse evidence_json into typed evidence items with source_type labels. */
interface EvidenceRef {
  source_type: string
  id?: number
  title?: string
  chunk_id?: number
  wiki_page_id?: number
  page_type?: string
}

function parseEvidence(raw: string): EvidenceRef[] {
  try {
    const arr = JSON.parse(raw)
    if (!Array.isArray(arr)) return []
    return arr.map((e: any) => {
      // Normalize different evidence shapes into a common form
      if (e.chunk_id) {
        return { source_type: 'knowledge_chunk', id: e.chunk_id, ...e }
      }
      if (e.wiki_page_id) {
        return { source_type: 'wiki_page', id: e.wiki_page_id, ...e }
      }
      if (e.source_id) {
        return { source_type: 'knowledge_source', id: e.source_id, ...e }
      }
      if (e.source_type) return e
      return { source_type: 'unknown', ...e }
    })
  } catch {
    return []
  }
}

function evidenceLabel(ref: EvidenceRef): string {
  const id = ref.id ?? ref.chunk_id ?? ref.wiki_page_id
  const title = ref.title ? `「${ref.title}」` : ''
  switch (ref.source_type) {
    case 'knowledge_chunk':
      return `知识片段 #${id}${title}`
    case 'wiki_page':
      return `Wiki 页面 #${id}${title}`
    case 'knowledge_source':
      return `知识来源 #${id}${title}`
    default:
      return ref.source_type ? `${ref.source_type} ${id ?? ''}${title}` : JSON.stringify(ref)
  }
}

/** Whether evidence is meaningful (not just an empty placeholder). */
function hasEvidence(raw: string): boolean {
  return parseEvidence(raw).length > 0
}

interface Props {
  item: WikiDiffItem | null
  onOpenChange: (v: boolean) => void
  onChanged: (item: WikiDiffItem) => void
}

export default function WikiDiffDetailDrawer({ item, onOpenChange, onChanged }: Props) {
  const hasPerm = useAuthStore((s) => s.hasPerm)
  const canApprove = hasPerm('wiki:approve')
  const [busy, setBusy] = useState(false)

  const evidenceRefs = useMemo(() => (item ? parseEvidence(item.evidence_json) : []), [item])

  const act = async (fn: () => Promise<any>, msg: string, patch: Partial<WikiDiffItem>) => {
    if (!item) return
    setBusy(true)
    try {
      const result = await fn()
      toast.success(msg)
      // If the function returned an artifact result, merge it into patch
      if (result && typeof result === 'object' && 'artifact_id' in result) {
        onChanged({ ...item, ...patch, resolved_artifact_id: result.artifact_id })
      } else {
        onChanged({ ...item, ...patch })
      }
    } catch (e: any) {
      toast.error(e?.message || '操作失败')
    } finally {
      setBusy(false)
    }
  }

  const handleAcceptAndCreate = async () => {
    if (!item) return
    setBusy(true)
    try {
      // Step 1: Accept the diff item
      await acceptWikiDiffItem(item.id)
      // Step 2: Create AI review artifact from the accepted item
      const result = await createWikiDiffArtifact(item.id)
      toast.success('已采纳并生成待审产物')
      onChanged({
        ...item,
        review_status: 'accepted',
        resolved_artifact_id: result.artifact_id,
      })
    } catch (e: any) {
      toast.error(e?.message || '操作失败')
    } finally {
      setBusy(false)
    }
  }

  if (!item) return null

  const sev = severityBadge(item.severity)

  return (
    <Sheet open={!!item} onOpenChange={onOpenChange}>
      <SheetContent className="sm:max-w-[540px] overflow-auto">
        <SheetHeader>
          <SheetTitle className="flex items-center gap-2 flex-wrap text-left">
            <Badge variant={sev.variant} className={sev.className} title={SEVERITY_LABEL[item.severity] ?? item.severity}>
              {item.severity}
            </Badge>
            <Badge variant="secondary">{item.dimension}</Badge>
            <Badge variant="outline">{item.diff_type}</Badge>
          </SheetTitle>
          <SheetDescription className="text-left text-foreground font-medium">{item.title}</SheetDescription>
        </SheetHeader>

        <div className="space-y-3 py-4 text-sm">
          {/* Left / Right comparison */}
          <div className="grid grid-cols-2 gap-2">
            <div className="rounded-md border p-2 bg-red-50/30 dark:bg-red-950/10">
              <div className="text-xs text-muted-foreground mb-1 font-medium">左侧 (RAG 知识库)</div>
              <div className="break-words whitespace-pre-wrap text-xs">{item.left_value || '—'}</div>
            </div>
            <div className="rounded-md border p-2 bg-green-50/30 dark:bg-green-950/10">
              <div className="text-xs text-muted-foreground mb-1 font-medium">右侧 (Wiki 知识库)</div>
              <div className="break-words whitespace-pre-wrap text-xs">{item.right_value || '—'}</div>
            </div>
          </div>

          {/* Suggestion */}
          {item.suggestion && (
            <div className="rounded-md border border-blue-200 bg-blue-50 p-2.5 text-blue-700 dark:border-blue-800 dark:bg-blue-950/40 dark:text-blue-300">
              <div className="text-xs font-medium mb-0.5">建议操作</div>
              <div className="text-xs">{item.suggestion}</div>
            </div>
          )}

          {/* Evidence references */}
          <div className="rounded-md border p-2.5">
            <div className="text-xs font-medium text-muted-foreground mb-1.5">
              证据来源 {evidenceRefs.length > 0 ? `(${evidenceRefs.length})` : '(无)'}
            </div>
            {evidenceRefs.length === 0 ? (
              <div className="text-xs text-muted-foreground italic">该差异项未附带来源引用</div>
            ) : (
              <div className="space-y-1">
                {evidenceRefs.map((ref, i) => (
                  <div key={i} className="flex items-center gap-1.5 text-xs">
                    <Badge variant="outline" className="text-[10px] px-1.5 py-0 h-4 font-normal">
                      {ref.source_type === 'knowledge_chunk' ? '知识片段' :
                       ref.source_type === 'wiki_page' ? 'Wiki 页面' :
                       ref.source_type === 'knowledge_source' ? '知识来源' :
                       ref.source_type}
                    </Badge>
                    <span className="text-muted-foreground truncate">{evidenceLabel(ref)}</span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Review status */}
          <div className="flex items-center gap-2 text-xs">
            <span className="text-muted-foreground">处理状态：</span>
            <Badge variant={item.review_status === 'accepted' ? 'default' : item.review_status === 'rejected' ? 'destructive' : 'outline'}>
              {item.review_status === 'accepted' ? '已采纳' :
               item.review_status === 'rejected' ? '已忽略' : '待处理'}
            </Badge>
            {item.resolved_artifact_id != null && (
              <span className="text-muted-foreground">已生成 AI 产物 #{item.resolved_artifact_id}</span>
            )}
          </div>
        </div>

        {canApprove && item.review_status === 'pending' && (
          <SheetFooter className="flex-row gap-2 sm:justify-start">
            <Button variant="outline" size="sm" disabled={busy}
              onClick={() => act(() => rejectWikiDiffItem(item.id), '已忽略', { review_status: 'rejected' })}>
              忽略
            </Button>
            <Button variant="outline" size="sm" disabled={busy}
              onClick={() => act(() => acceptWikiDiffItem(item.id), '已确认', { review_status: 'accepted' })}>
              仅确认
            </Button>
            <Button size="sm" disabled={busy}
              onClick={handleAcceptAndCreate}>
              采纳并生成待审产物
            </Button>
          </SheetFooter>
        )}

        {canApprove && item.review_status === 'accepted' && !item.resolved_artifact_id && (
          <SheetFooter className="flex-row gap-2 sm:justify-start pt-2">
            <Button size="sm" disabled={busy}
              onClick={() => act(
                async () => { const r = await createWikiDiffArtifact(item.id); return r },
                '已生成待审产物', { review_status: 'accepted' })}>
              生成待审产物
            </Button>
          </SheetFooter>
        )}

        {item.review_status === 'rejected' && (
          <SheetFooter className="flex-row gap-2 sm:justify-start pt-2">
            <Button variant="outline" size="sm" disabled={busy}
              onClick={() => act(() => acceptWikiDiffItem(item.id), '已重新采纳', { review_status: 'accepted' })}>
              重新采纳
            </Button>
          </SheetFooter>
        )}
      </SheetContent>
    </Sheet>
  )
}
