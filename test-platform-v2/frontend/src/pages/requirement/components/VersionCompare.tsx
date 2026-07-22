/** VersionCompare — side-by-side diff view for two versions of a requirement document.
 *
 * Batch-28: Deferred from batch-26 C1. Shows pages from diff_json with change type
 * indicators and OCR diff snippets. Left = old version, Right = new version.
 */
import { useState, useCallback } from 'react'
import {
  Dialog, DialogContent, DialogHeader, DialogTitle,
} from '@/components/ui/dialog'
import { Badge } from '@/components/ui/badge'
import { Switch } from '@/components/ui/switch'
import { Label } from '@/components/ui/label'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Skeleton } from '@/components/ui/skeleton'
import { cn } from '@/lib/utils'
import {
  GitCompare, ArrowRight, Plus, Minus, Pencil, Trash2,
} from 'lucide-react'

// ── Types ──

interface DiffPage {
  page_index: number
  page_name: string
  page_path: string
  change_type: 'new' | 'modified' | 'unchanged' | 'deleted'
  text_similarity: number
  screenshot_hash: string
  prev_screenshot_hash: string
  ocr_diff: string
}

interface DiffSummary {
  total_pages: number
  new_pages: number
  modified_pages: number
  unchanged_pages: number
  deleted_pages: number
}

interface DiffData {
  summary: DiffSummary
  pages: DiffPage[]
  base_version: string
  base_job_id: number
  current_version: string
  current_job_id: number
}

interface VersionCompareProps {
  open: boolean
  onClose: () => void
  diffData: DiffData | null
}

// ── Change type config ──

const CHANGE_CONFIG: Record<string, { icon: typeof Plus; label: string; color: string; bg: string }> = {
  new:       { icon: Plus,       label: '新增',   color: 'text-green-600',  bg: 'bg-green-50 border-green-200' },
  modified:  { icon: Pencil,     label: '修改',   color: 'text-amber-600',  bg: 'bg-amber-50 border-amber-200' },
  unchanged: { icon: ArrowRight, label: '不变',   color: 'text-slate-500',  bg: 'bg-slate-50 border-slate-200' },
  deleted:   { icon: Trash2,     label: '已删除', color: 'text-red-600',    bg: 'bg-red-50 border-red-200' },
}

// ── Sub-component: single page diff row ──

function PageDiffRow({ page, syncScrollRef }: { page: DiffPage; syncScrollRef?: (el: HTMLDivElement | null) => void }) {
  const cfg = CHANGE_CONFIG[page.change_type] || CHANGE_CONFIG.unchanged
  const Icon = cfg.icon

  return (
    <div className={cn('border rounded-lg p-3 mb-2', cfg.bg)}>
      <div className="flex items-center gap-2 mb-1">
        <Icon className={cn('size-3.5', cfg.color)} />
        <Badge variant="outline" className={cn('text-xs', cfg.color)}>
          {cfg.label}
        </Badge>
        <span className="text-sm font-medium truncate flex-1">{page.page_name}</span>
        {page.change_type !== 'deleted' && page.change_type !== 'new' && (
          <span className="text-xs text-muted-foreground">
            相似度: {(page.text_similarity * 100).toFixed(0)}%
          </span>
        )}
      </div>

      {/* OCR diff snippet */}
      {page.ocr_diff && (
        <div className="text-xs text-muted-foreground mt-1.5 pl-5 space-y-0.5">
          {page.ocr_diff.split('; ').map((part, i) => {
            const isRemove = part.startsWith('移除:')
            const isAdd = part.startsWith('新增:')
            const cn = isRemove
              ? 'text-red-600 line-through'
              : isAdd
                ? 'text-green-600'
                : 'text-amber-600'
            return (
              <div key={i} className={cn}>
                {part}
              </div>
            )
          })}
        </div>
      )}

      {/* Empty state for unchanged/deleted */}
      {!page.ocr_diff && page.change_type === 'unchanged' && (
        <p className="text-xs text-muted-foreground pl-5 mt-1">页面无变更</p>
      )}
      {!page.ocr_diff && page.change_type === 'deleted' && (
        <p className="text-xs text-red-500 pl-5 mt-1">此页面在新版本中已删除</p>
      )}
    </div>
  )
}

// ── Main component ──

export default function VersionCompare({ open, onClose, diffData }: VersionCompareProps) {
  const [syncScroll, setSyncScroll] = useState(true)

  const leftRef = useCallback((el: HTMLDivElement | null) => {
    if (!el || !syncScroll) return
    const onScroll = () => {
      const right = document.getElementById('vc-right-panel')
      if (right) right.scrollTop = el.scrollTop
    }
    el.addEventListener('scroll', onScroll)
    return () => el.removeEventListener('scroll', onScroll)
  }, [syncScroll])

  const rightRef = useCallback((el: HTMLDivElement | null) => {
    if (!el || !syncScroll) return
    const onScroll = () => {
      const left = document.getElementById('vc-left-panel')
      if (left) left.scrollTop = el.scrollTop
    }
    el.addEventListener('scroll', onScroll)
    return () => el.removeEventListener('scroll', onScroll)
  }, [syncScroll])

  if (!diffData) {
    return (
      <Dialog open={open} onOpenChange={(nextOpen) => { if (!nextOpen) onClose() }}>
        <DialogContent className="max-w-[95vw] max-h-[90vh] w-full">
          <DialogHeader>
            <DialogTitle>版本对比</DialogTitle>
          </DialogHeader>
          <div className="flex items-center justify-center py-12 text-muted-foreground">
            暂无对比数据
          </div>
        </DialogContent>
      </Dialog>
    )
  }

  const { summary, pages, base_version, current_version } = diffData

  return (
    <Dialog open={open} onOpenChange={(o) => { if (!o) onClose() }}>
      <DialogContent className="max-w-[95vw] max-h-[90vh] w-full">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <GitCompare className="size-5" />
            版本对比: {base_version} → {current_version}
          </DialogTitle>
        </DialogHeader>

        {/* Summary bar */}
        <div className="flex items-center gap-3 flex-wrap text-xs text-muted-foreground">
          <span className="text-green-600">🆕 {summary.new_pages} 新增</span>
          <span className="text-amber-600">✏️ {summary.modified_pages} 修改</span>
          <span className="text-slate-500">➡️ {summary.unchanged_pages} 不变</span>
          <span className="text-red-600">❌ {summary.deleted_pages} 删除</span>
          <span className="ml-auto flex items-center gap-2">
            <Switch
              id="sync-scroll"
              checked={syncScroll}
              onCheckedChange={setSyncScroll}
              className="scale-75"
            />
            <Label htmlFor="sync-scroll" className="text-xs cursor-pointer">
              同步滚动
            </Label>
          </span>
        </div>

        {/* Side-by-side panels */}
        <div className="grid grid-cols-2 gap-4 h-[60vh]">
          {/* Left: old version */}
          <div className="flex flex-col">
            <div className="text-sm font-semibold mb-2 text-muted-foreground">
              旧版本 ({base_version})
            </div>
            <ScrollArea id="vc-left-panel" ref={leftRef} className="flex-1 border rounded-lg p-3">
              {pages
                .filter((p) => p.change_type !== 'new')
                .map((p) => (
                  <PageDiffRow key={`l-${p.page_index}`} page={p} />
                ))}
              {pages.filter((p) => p.change_type !== 'new').length === 0 && (
                <div className="text-center text-muted-foreground py-8 text-sm">
                  全部为新增页面
                </div>
              )}
            </ScrollArea>
          </div>

          {/* Right: new version */}
          <div className="flex flex-col">
            <div className="text-sm font-semibold mb-2">
              新版本 ({current_version})
            </div>
            <ScrollArea id="vc-right-panel" ref={rightRef} className="flex-1 border rounded-lg p-3">
              {pages
                .filter((p) => p.change_type !== 'deleted')
                .map((p) => (
                  <PageDiffRow key={`r-${p.page_index}`} page={p} />
                ))}
              {pages.filter((p) => p.change_type !== 'deleted').length === 0 && (
                <div className="text-center text-muted-foreground py-8 text-sm">
                  全部为已删除页面
                </div>
              )}
            </ScrollArea>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
