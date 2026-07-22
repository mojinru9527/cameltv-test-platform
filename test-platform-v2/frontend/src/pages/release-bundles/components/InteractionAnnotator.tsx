import { useState, useRef, useCallback, useEffect } from 'react'
import { toast } from 'sonner'
import { saveInteractions } from '@/api/requirementModules'
import type { ModuleTreeNode } from '@/types'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Checkbox } from '@/components/ui/checkbox'
import { Trash2, Move, Plus } from '@/lib/icons'
import { cn } from '@/lib/utils'

interface AnnotatedRegion {
  id: string
  x: number
  y: number
  width: number
  height: number
  targetPage: string
  interactionType: string
  trigger: string
  sourceElement: string
  adminConfigSource: string
  isGlobalNav: boolean
}

interface InteractionAnnotatorProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  page: ModuleTreeNode | null
  screenshotUrls: string[]
  allPages: string[]
}

const INTERACTION_TYPES = [
  { value: 'navigation', label: '页面跳转' },
  { value: 'modal', label: '弹窗' },
  { value: 'tab_switch', label: 'Tab 切换' },
  { value: 'external', label: '外链' },
  { value: 'dynamic_filter', label: '动态筛选' },
]

export default function InteractionAnnotator({
  open,
  onOpenChange,
  page,
  screenshotUrls,
  allPages,
}: InteractionAnnotatorProps) {
  const canvasRef = useRef<HTMLDivElement>(null)
  const imgRef = useRef<HTMLImageElement>(null)
  const [regions, setRegions] = useState<AnnotatedRegion[]>([])
  const [drawing, setDrawing] = useState(false)
  const [startPos, setStartPos] = useState({ x: 0, y: 0 })
  const [currentRect, setCurrentRect] = useState<{ x: number; y: number; w: number; h: number } | null>(null)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [selectedImage, setSelectedImage] = useState(0)
  const [saving, setSaving] = useState(false)

  // Parse existing interactions
  useEffect(() => {
    if (page?.page_interactions) {
      try {
        const existing = JSON.parse(page.page_interactions)
        // Convert to regions (approximate coordinates not available from JSON)
        setRegions([])
      } catch {
        setRegions([])
      }
    } else {
      setRegions([])
    }
  }, [page])

  // Canvas mouse handlers
  const getRelativePos = useCallback(
    (e: React.MouseEvent) => {
      if (!canvasRef.current) return { x: 0, y: 0 }
      const rect = canvasRef.current.getBoundingClientRect()
      return {
        x: e.clientX - rect.left,
        y: e.clientY - rect.top,
      }
    },
    [],
  )

  const handleMouseDown = (e: React.MouseEvent) => {
    if (editingId) return
    const pos = getRelativePos(e)
    setStartPos(pos)
    setDrawing(true)
    setCurrentRect({ x: pos.x, y: pos.y, w: 0, h: 0 })
  }

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!drawing) return
    const pos = getRelativePos(e)
    setCurrentRect({
      x: Math.min(startPos.x, pos.x),
      y: Math.min(startPos.y, pos.y),
      w: Math.abs(pos.x - startPos.x),
      h: Math.abs(pos.y - startPos.y),
    })
  }

  const handleMouseUp = () => {
    if (!drawing || !currentRect) return
    setDrawing(false)
    // Only create a region if it has minimum size
    if (currentRect.w < 10 || currentRect.h < 10) {
      setCurrentRect(null)
      return
    }
    const newId = `region-${Date.now()}`
    const newRegion: AnnotatedRegion = {
      id: newId,
      x: currentRect.x,
      y: currentRect.y,
      width: currentRect.w,
      height: currentRect.h,
      targetPage: '',
      interactionType: 'navigation',
      trigger: '',
      sourceElement: '',
      adminConfigSource: '',
      isGlobalNav: false,
    }
    setRegions((prev) => [...prev, newRegion])
    setEditingId(newId)
    setCurrentRect(null)
  }

  const updateRegion = (id: string, updates: Partial<AnnotatedRegion>) => {
    setRegions((prev) =>
      prev.map((r) => (r.id === id ? { ...r, ...updates } : r)),
    )
  }

  const deleteRegion = (id: string) => {
    setRegions((prev) => prev.filter((r) => r.id !== id))
    if (editingId === id) setEditingId(null)
  }

  const handleSave = async () => {
    if (!page) return
    setSaving(true)
    try {
      const interactions = regions
        .filter((r) => r.targetPage)
        .map((r) => ({
          trigger: r.trigger || '点击交互区域',
          target_page: r.targetPage,
          interaction_type: r.isGlobalNav ? 'global_navigation' : r.interactionType,
          source_element: r.sourceElement || undefined,
          admin_config_source: r.adminConfigSource || undefined,
        }))
      await saveInteractions(page.id, { interactions, merge: true })
      toast.success(`已保存 ${interactions.length} 个交互标注`)
      onOpenChange(false)
    } catch {
      toast.error('保存失败')
    } finally {
      setSaving(false)
    }
  }

  const imageUrl = screenshotUrls[selectedImage]

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-[95vw] max-h-[90vh] w-[1200px] p-0">
        <DialogHeader className="p-4 pb-2 border-b">
          <DialogTitle className="text-base flex items-center gap-2">
            页面交互标注 — {page?.name ?? '未知页面'}
          </DialogTitle>
        </DialogHeader>

        <div className="flex h-[70vh]">
          {/* Screenshot Canvas */}
          <div className="flex-1 relative bg-muted/20 overflow-hidden">
            {imageUrl ? (
              <div
                ref={canvasRef}
                className="relative w-full h-full cursor-crosshair select-none"
                onMouseDown={handleMouseDown}
                onMouseMove={handleMouseMove}
                onMouseUp={handleMouseUp}
                onMouseLeave={handleMouseUp}
              >
                <img
                  ref={imgRef}
                  src={imageUrl}
                  alt={page?.name ?? 'Screenshot'}
                  className="max-w-full max-h-full object-contain mx-auto"
                  draggable={false}
                />
                {/* Saved regions */}
                {regions.map((r) => (
                  <div
                    key={r.id}
                    className={cn(
                      'absolute border-2 rounded-sm transition-colors',
                      editingId === r.id
                        ? 'border-blue-500 bg-blue-500/20'
                        : r.isGlobalNav
                          ? 'border-purple-500 bg-purple-500/10'
                          : 'border-green-500 bg-green-500/10',
                    )}
                    style={{
                      left: r.x,
                      top: r.y,
                      width: r.width,
                      height: r.height,
                    }}
                    onClick={(e) => {
                      e.stopPropagation()
                      setEditingId(r.id)
                    }}
                  >
                    {r.targetPage && (
                      <span className="absolute -top-5 left-0 text-xs bg-background/90 px-1 rounded whitespace-nowrap">
                        → {r.targetPage}
                      </span>
                    )}
                  </div>
                ))}
                {/* Current drawing rect */}
                {currentRect && (
                  <div
                    className="absolute border-2 border-blue-400 bg-blue-400/10 rounded-sm"
                    style={{
                      left: currentRect.x,
                      top: currentRect.y,
                      width: currentRect.w,
                      height: currentRect.h,
                    }}
                  />
                )}
              </div>
            ) : (
              <div className="flex items-center justify-center h-full text-muted-foreground">
                <div className="text-center">
                  <p>暂无截图</p>
                  <p className="text-xs mt-1">请先在知识源中上传页面截图</p>
                </div>
              </div>
            )}
          </div>

          {/* Right Panel: Annotation List */}
          <div className="w-80 shrink-0 border-l flex flex-col">
            <ScrollArea className="flex-1 p-4">
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <h4 className="text-sm font-semibold">标注列表 ({regions.length})</h4>
                  {editingId && (
                    <Button
                      variant="ghost"
                      size="sm"
                      className="text-xs"
                      onClick={() => setEditingId(null)}
                    >
                      完成编辑
                    </Button>
                  )}
                </div>

                {regions.length === 0 ? (
                  <p className="text-xs text-muted-foreground text-center py-8">
                    在左侧截图上拖拽鼠标绘制矩形区域
                  </p>
                ) : (
                  regions.map((r) => (
                    <div
                      key={r.id}
                      className={cn(
                        'border rounded-md p-3 space-y-2',
                        editingId === r.id
                          ? 'border-blue-300 bg-blue-50/50'
                          : 'border-border',
                      )}
                    >
                      <div className="flex items-center gap-2">
                        <Move className="h-3 w-3 text-muted-foreground" />
                        <span className="text-xs font-medium flex-1">
                          区域 {r.id.slice(-4)}
                        </span>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-6 w-6 text-muted-foreground hover:text-destructive"
                          onClick={() => deleteRegion(r.id)}
                        >
                          <Trash2 className="h-3 w-3" />
                        </Button>
                      </div>

                      {editingId === r.id ? (
                        <>
                          <div>
                            <Label className="text-xs">目标页面</Label>
                            <Select
                              value={r.targetPage}
                              onValueChange={(v) =>
                                updateRegion(r.id, { targetPage: v })
                              }
                            >
                              <SelectTrigger className="h-8 text-xs">
                                <SelectValue placeholder="选择目标页面" />
                              </SelectTrigger>
                              <SelectContent>
                                {allPages.map((p) => (
                                  <SelectItem key={p} value={p} className="text-xs">
                                    {p}
                                  </SelectItem>
                                ))}
                              </SelectContent>
                            </Select>
                          </div>
                          <div>
                            <Label className="text-xs">交互类型</Label>
                            <Select
                              value={r.interactionType}
                              onValueChange={(v) =>
                                updateRegion(r.id, { interactionType: v })
                              }
                            >
                              <SelectTrigger className="h-8 text-xs">
                                <SelectValue />
                              </SelectTrigger>
                              <SelectContent>
                                {INTERACTION_TYPES.map((t) => (
                                  <SelectItem
                                    key={t.value}
                                    value={t.value}
                                    className="text-xs"
                                  >
                                    {t.label}
                                  </SelectItem>
                                ))}
                              </SelectContent>
                            </Select>
                          </div>
                          <div>
                            <Label className="text-xs">触发元素</Label>
                            <Input
                              className="h-8 text-xs"
                              value={r.sourceElement}
                              onChange={(e) =>
                                updateRegion(r.id, {
                                  sourceElement: e.target.value,
                                })
                              }
                              placeholder="如: 顶部搜索栏"
                            />
                          </div>
                          {r.interactionType === 'dynamic_filter' && (
                            <div>
                              <Label className="text-xs">运营后台配置源</Label>
                              <Input
                                className="h-8 text-xs"
                                value={r.adminConfigSource}
                                onChange={(e) =>
                                  updateRegion(r.id, {
                                    adminConfigSource: e.target.value,
                                  })
                                }
                                placeholder="如: 资讯分类配置"
                              />
                            </div>
                          )}
                          <div className="flex items-center gap-2">
                            <Checkbox
                              id={`gn-${r.id}`}
                              checked={r.isGlobalNav}
                              onCheckedChange={(checked) =>
                                updateRegion(r.id, {
                                  isGlobalNav: !!checked,
                                })
                              }
                            />
                            <Label
                              htmlFor={`gn-${r.id}`}
                              className="text-xs cursor-pointer"
                            >
                              全局导航入口
                            </Label>
                          </div>
                        </>
                      ) : (
                        <div className="text-xs space-y-1">
                          <p>
                            →{' '}
                            <span className="font-medium text-blue-600">
                              {r.targetPage || '未设置'}
                            </span>
                          </p>
                          <Badge variant="outline" className="text-xs">
                            {INTERACTION_TYPES.find(
                              (t) => t.value === r.interactionType,
                            )?.label ?? r.interactionType}
                          </Badge>
                          {r.isGlobalNav && (
                            <Badge className="text-xs ml-1 bg-purple-100 text-purple-700">
                              全局导航
                            </Badge>
                          )}
                        </div>
                      )}
                    </div>
                  ))
                )}
              </div>
            </ScrollArea>

            {/* Bottom actions */}
            <div className="p-3 border-t flex gap-2">
              <Button
                variant="default"
                size="sm"
                className="flex-1"
                onClick={handleSave}
                disabled={saving || regions.length === 0}
              >
                {saving ? '保存中...' : '保存'}
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => onOpenChange(false)}
              >
                取消
              </Button>
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
