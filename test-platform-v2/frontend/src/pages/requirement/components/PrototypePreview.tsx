/** PrototypePreview — screenshot preview for lanhu evidence pages.
 *
 * Batch-28: Deferred from batch-26 C1. Displays lanhu prototype screenshots
 * with OCR sidebar, zoom/drag, and keyboard navigation.
 */
import { useState, useEffect, useCallback, useRef } from 'react'
import {
  Dialog, DialogContent, DialogHeader, DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/ui'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Skeleton } from '@/components/ui/skeleton'
import { Badge } from '@/ui'
import { cn } from '@/lib/utils'
import { downloadLanhuEvidenceAsset } from '@/api/lanhuEvidence'
import {
  Image, ChevronLeft, ChevronRight, Download, ZoomIn, ZoomOut, RotateCcw,
} from 'lucide-react'

// ── Types ──

export interface ScreenshotPage {
  page_name: string
  page_index: number
  ocr_text?: string
  asset_id?: number
  interactions?: string
}

interface PrototypePreviewProps {
  open: boolean
  onClose: () => void
  pages: ScreenshotPage[]
  initialPageIndex?: number
  version?: string
}

// ── Main component ──

export default function PrototypePreview({
  open,
  onClose,
  pages,
  initialPageIndex = 0,
  version,
}: PrototypePreviewProps) {
  const [currentIndex, setCurrentIndex] = useState(initialPageIndex)
  const [scale, setScale] = useState(1)
  const [position, setPosition] = useState({ x: 0, y: 0 })
  const [isDragging, setIsDragging] = useState(false)
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 })
  const [imageError, setImageError] = useState(false)
  const [imageUrl, setImageUrl] = useState<string | null>(null)
  const [imageLoading, setImageLoading] = useState(false)
  const imageRef = useRef<HTMLDivElement>(null)

  const total = pages.length
  const current = pages[currentIndex] || null

  const goTo = useCallback((idx: number) => {
    if (idx >= 0 && idx < total) setCurrentIndex(idx)
  }, [total])

  // Reset on page change
  useEffect(() => {
    setScale(1)
    setPosition({ x: 0, y: 0 })
    setImageError(false)
  }, [currentIndex])

  useEffect(() => {
    if (!open || current?.asset_id == null) {
      setImageUrl(null)
      setImageLoading(false)
      return
    }

    const controller = new AbortController()
    let objectUrl: string | null = null
    setImageUrl(null)
    setImageError(false)
    setImageLoading(true)

    downloadLanhuEvidenceAsset(current.asset_id, controller.signal)
      .then((blob) => {
        if (controller.signal.aborted) return
        objectUrl = URL.createObjectURL(blob)
        setImageUrl(objectUrl)
      })
      .catch(() => {
        if (!controller.signal.aborted) setImageError(true)
      })
      .finally(() => {
        if (!controller.signal.aborted) setImageLoading(false)
      })

    return () => {
      controller.abort()
      if (objectUrl) URL.revokeObjectURL(objectUrl)
    }
  }, [open, current?.asset_id])

  // Keyboard navigation
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (!open) return
      if (e.key === 'ArrowLeft') goTo(currentIndex - 1)
      if (e.key === 'ArrowRight') goTo(currentIndex + 1)
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, currentIndex, goTo, onClose])

  // Wheel zoom
  const handleWheel = useCallback((e: React.WheelEvent) => {
    e.preventDefault()
    setScale((s) => Math.min(3, Math.max(0.5, s + (e.deltaY > 0 ? -0.1 : 0.1))))
  }, [])

  // Drag handlers
  const handleMouseDown = (e: React.MouseEvent) => {
    if (scale <= 1) return
    setIsDragging(true)
    setDragStart({ x: e.clientX - position.x, y: e.clientY - position.y })
  }
  const handleMouseMove = (e: React.MouseEvent) => {
    if (!isDragging) return
    setPosition({ x: e.clientX - dragStart.x, y: e.clientY - dragStart.y })
  }
  const handleMouseUp = () => setIsDragging(false)

  const resetView = () => {
    setScale(1)
    setPosition({ x: 0, y: 0 })
  }

  // ── Empty state ──
  if (!pages.length) {
    return (
      <Dialog open={open} onOpenChange={(o) => { if (!o) onClose() }}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Image className="size-5" />
              蓝湖原型截图
            </DialogTitle>
          </DialogHeader>
          <div className="text-center py-12 text-muted-foreground">
            <Image className="size-12 mx-auto mb-3 opacity-30" />
            <p className="text-sm">该任务暂无截图</p>
            <p className="text-xs mt-1">请确认证据采集已完成且包含截图资产</p>
          </div>
        </DialogContent>
      </Dialog>
    )
  }

  return (
    <Dialog open={open} onOpenChange={(o) => { if (!o) onClose() }}>
      <DialogContent className="max-w-[92vw] max-h-[92vh] w-full">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-base">
            <Image className="size-4" />
            蓝湖原型截图
            {version && (
              <Badge tone="neutral" className="text-xs ml-1">{version}</Badge>
            )}
            {current && (
              <span className="text-muted-foreground font-normal text-sm ml-2 truncate">
                · {current.page_name}
              </span>
            )}
          </DialogTitle>
        </DialogHeader>

        <div className="grid max-h-[70vh] min-h-0 grid-cols-1 gap-4 overflow-y-auto md:h-[70vh] md:grid-cols-[minmax(0,1fr)_300px] md:overflow-hidden">
          {/* Left: screenshot area */}
          <div className="relative flex min-h-[320px] items-center justify-center overflow-hidden rounded-lg bg-muted md:h-full">
            {/* Toolbar */}
            <div className="absolute top-2 right-2 z-10 flex gap-1">
              <Button
                size="icon"
                variant="ghost"
                className="min-h-11 min-w-11 sm:size-7 sm:min-h-0 sm:min-w-0"
                onClick={() => setScale((s) => Math.min(3, s + 0.2))}
                aria-label="放大截图"
              >
                <ZoomIn className="size-3.5" />
              </Button>
              <Button
                size="icon"
                variant="ghost"
                className="min-h-11 min-w-11 sm:size-7 sm:min-h-0 sm:min-w-0"
                onClick={() => setScale((s) => Math.max(0.5, s - 0.2))}
                aria-label="缩小截图"
              >
                <ZoomOut className="size-3.5" />
              </Button>
              <Button
                size="icon"
                variant="ghost"
                className="min-h-11 min-w-11 sm:size-7 sm:min-h-0 sm:min-w-0"
                onClick={resetView}
                aria-label="重置截图缩放"
              >
                <RotateCcw className="size-3.5" />
              </Button>
              <span className="text-xs text-muted-foreground self-center px-1 tabular-nums">
                {Math.round(scale * 100)}%
              </span>
            </div>

            {/* Image with drag/zoom */}
            <div
              ref={imageRef}
              className={cn('select-none', scale > 1 ? 'cursor-grab' : 'cursor-default')}
              onWheel={handleWheel}
              onMouseDown={handleMouseDown}
              onMouseMove={handleMouseMove}
              onMouseUp={handleMouseUp}
              onMouseLeave={handleMouseUp}
              style={{ transform: `translate(${position.x}px, ${position.y}px) scale(${scale})`, transition: isDragging ? 'none' : 'transform 0.15s' }}
            >
              {imageLoading ? (
                <Skeleton className="h-3/4 w-3/4" />
              ) : imageUrl && !imageError ? (
                <img
                  src={imageUrl}
                  alt={current.page_name}
                  className="max-w-full max-h-[65vh] object-contain"
                  onError={() => setImageError(true)}
                  draggable={false}
                />
              ) : (
                <div className="flex flex-col items-center justify-center p-12 text-muted-foreground">
                  <Image className="size-16 mb-3 opacity-20" />
                  <p className="text-sm">截图不可用</p>
                  <p className="text-xs mt-1">
                    {current?.asset_id == null ? '该页面没有截图资产' : '截图文件已失效（部署重建存储后旧截图不可用，请重新采集）'}
                  </p>
                </div>
              )}
            </div>

            {/* Navigation arrows */}
            {total > 1 && (
              <>
                <Button
                  size="icon" variant="ghost"
                  className="absolute left-2 top-1/2 -translate-y-1/2 size-8 bg-card/80 shadow"
                  disabled={currentIndex === 0}
                  onClick={() => goTo(currentIndex - 1)}
                  aria-label="上一张截图"
                >
                  <ChevronLeft className="size-4" />
                </Button>
                <Button
                  size="icon" variant="ghost"
                  className="absolute right-2 top-1/2 -translate-y-1/2 size-8 bg-card/80 shadow"
                  disabled={currentIndex === total - 1}
                  onClick={() => goTo(currentIndex + 1)}
                  aria-label="下一张截图"
                >
                  <ChevronRight className="size-4" />
                </Button>
              </>
            )}

            {/* Page counter */}
            <div className="absolute bottom-2 left-1/2 -translate-x-1/2 bg-[var(--color-overlay-scrim)] text-[var(--color-text-inverse)] text-xs px-2.5 py-1 rounded-full">
              {currentIndex + 1} / {total}
            </div>
          </div>

          {/* Right: OCR text panel */}
          <div className="flex min-h-0 flex-col overflow-hidden rounded-lg border md:h-full">
            <div className="px-3 py-2 border-b bg-muted/30 text-sm font-medium">
              OCR 文字
            </div>
            <ScrollArea className="min-h-0 flex-1">
              <div className="p-3 text-xs text-muted-foreground whitespace-pre-wrap leading-relaxed">
                {current?.ocr_text || '该页面无 OCR 文字'}
              </div>
              {current?.interactions && (
                <>
                  <div className="px-3 py-2 border-t bg-muted/30 text-sm font-medium">
                    交互说明
                  </div>
                  <div className="p-3 text-xs text-muted-foreground whitespace-pre-wrap">
                    {current.interactions}
                  </div>
                </>
              )}
            </ScrollArea>
          </div>
        </div>

        {/* Footer */}
        <div className="mt-1 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex flex-wrap items-center gap-2">
            <Button size="sm" variant="secondary" onClick={() => goTo(currentIndex - 1)} disabled={currentIndex === 0}>
              <ChevronLeft className="size-3.5 mr-1" />上一页
            </Button>
            <Button size="sm" variant="secondary" onClick={() => goTo(currentIndex + 1)} disabled={currentIndex === total - 1}>
              下一页<ChevronRight className="size-3.5 ml-1" />
            </Button>
          </div>
          {imageUrl && (
            <a href={imageUrl} target="_blank" rel="noopener noreferrer" download={`${current?.page_name || 'screenshot'}.png`}
               className="ui-btn ui-btn-ghost ui-btn-sm inline-flex">
              <Download className="size-3.5 mr-1" />下载原图
            </a>
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}
