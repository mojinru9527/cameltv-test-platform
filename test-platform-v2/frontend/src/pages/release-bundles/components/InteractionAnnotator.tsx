import { useState, useRef, useCallback, useEffect } from 'react'
import { toast } from 'sonner'
import { saveInteractions } from '@/api/requirementModules'
import type { ModuleTreeNode } from '@/types'
import { Button } from '@/ui'
import { Input } from '@/ui'
import { Label } from '@/components/ui/label'
import { Badge } from '@/ui'
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

export interface AnnotatedRegion {
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
  coordinateStatus: 'verified' | 'missing'
}

export interface ParsedSavedRegions {
  regions: AnnotatedRegion[]
  error: string
}

function optionalFiniteNumber(value: unknown): number | null {
  return typeof value === 'number' && Number.isFinite(value) ? value : null
}

function hasValidCoordinates(region: Pick<AnnotatedRegion, 'x' | 'y' | 'width' | 'height'>) {
  return [region.x, region.y, region.width, region.height].every(Number.isFinite)
    && region.x >= 0
    && region.y >= 0
    && region.width > 0
    && region.height > 0
}

export function parseSavedRegions(rawJson: string): ParsedSavedRegions {
  let parsed: unknown
  try {
    parsed = JSON.parse(rawJson || '[]')
  } catch {
    return { regions: [], error: '历史交互标注 JSON 已损坏，请先修复或迁移后再保存。' }
  }
  if (!Array.isArray(parsed)) {
    return { regions: [], error: '历史交互标注不是数组格式，请先完成数据迁移。' }
  }

  let invalidEntries = 0
  const regions = parsed.flatMap((value, index) => {
    if (!value || typeof value !== 'object') {
      invalidEntries += 1
      return []
    }

    const item = value as Record<string, unknown>
    const interactionType = String(item.interaction_type || 'navigation')
    const x = optionalFiniteNumber(item.x)
    const y = optionalFiniteNumber(item.y)
    const width = optionalFiniteNumber(item.width)
    const height = optionalFiniteNumber(item.height)
    const coordinateStatus: AnnotatedRegion['coordinateStatus'] = x !== null && y !== null && width !== null && height !== null
      && x >= 0 && y >= 0 && width > 0 && height > 0
      ? 'verified'
      : 'missing'
    return [{
      id: String(item.id || `saved-region-${index}`),
      x: x ?? 0,
      y: y ?? 0,
      width: width ?? 0,
      height: height ?? 0,
      targetPage: String(item.target_page || ''),
      interactionType,
      trigger: String(item.trigger || ''),
      sourceElement: String(item.source_element || ''),
      adminConfigSource: String(item.admin_config_source || ''),
      isGlobalNav: interactionType === 'global_navigation' || item.is_global_nav === true,
      coordinateStatus,
    }]
  })

  const error = invalidEntries > 0 ? `${invalidEntries} 条无效历史记录未载入，请先完成数据迁移。` : ''
  return { regions, error }
}

export function serializeRegions(regions: AnnotatedRegion[]) {
  if (regions.some((region) => !region.targetPage)) {
    throw new Error('每个交互标注都必须选择目标页面')
  }
  if (regions.some((region) => region.coordinateStatus !== 'verified' || !hasValidCoordinates(region))) {
    throw new Error('存在缺少真实坐标的旧标注，请重新定位后再保存')
  }
  return regions.map((region) => ({
    id: region.id,
    trigger: region.trigger || '点击交互区域',
    target_page: region.targetPage,
    interaction_type: region.isGlobalNav ? 'global_navigation' : region.interactionType,
    source_element: region.sourceElement || undefined,
    admin_config_source: region.adminConfigSource || undefined,
    x: region.x,
    y: region.y,
    width: region.width,
    height: region.height,
  }))
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
  const [historyError, setHistoryError] = useState('')

  // Parse existing interactions
  useEffect(() => {
    const parsed = parseSavedRegions(page?.page_interactions ?? '[]')
    setRegions(parsed.regions)
    setHistoryError(parsed.error)
    setEditingId(null)
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
      coordinateStatus: 'verified',
    }
    setRegions((prev) => [...prev, newRegion])
    setEditingId(newId)
    setCurrentRect(null)
  }

  const updateRegion = (id: string, updates: Partial<AnnotatedRegion>) => {
    setRegions((prev) =>
      prev.map((region) => {
        if (region.id !== id) return region
        const next = { ...region, ...updates }
        return {
          ...next,
          coordinateStatus: hasValidCoordinates(next) ? 'verified' : 'missing',
        }
      }),
    )
  }

  const deleteRegion = (id: string) => {
    setRegions((prev) => prev.filter((r) => r.id !== id))
    if (editingId === id) setEditingId(null)
  }

  const addKeyboardRegion = () => {
    const newId = `region-${Date.now()}`
    setRegions((prev) => [
      ...prev,
      {
        id: newId,
        x: 24,
        y: 24,
        width: 140,
        height: 88,
        targetPage: '',
        interactionType: 'navigation',
        trigger: '',
        sourceElement: '',
        adminConfigSource: '',
        isGlobalNav: false,
        coordinateStatus: 'verified',
      },
    ])
    setEditingId(newId)
  }

  const handleSave = async () => {
    if (!page) return
    setSaving(true)
    try {
      const interactions = serializeRegions(regions)
      await saveInteractions(page.id, { interactions, merge: false })
      toast.success(`已保存 ${interactions.length} 个交互标注`)
      onOpenChange(false)
    } catch (reason) {
      toast.error(reason instanceof Error ? reason.message : '保存失败')
    } finally {
      setSaving(false)
    }
  }

  const imageUrl = screenshotUrls[selectedImage]

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[94dvh] w-[min(1200px,96vw)] sm:max-w-[96vw] overflow-hidden p-0">
        <DialogHeader className="p-4 pb-2 border-b">
          <DialogTitle className="text-base flex items-center gap-2">
            页面交互标注 — {page?.name ?? '未知页面'}
          </DialogTitle>
        </DialogHeader>

        <div className="flex h-[82dvh] min-h-0 flex-col lg:h-[70vh] lg:flex-row">
          {/* Screenshot Canvas */}
          <div className="relative min-h-[34dvh] flex-1 overflow-hidden bg-muted/20">
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
                {regions.filter((region) => region.coordinateStatus === 'verified').map((r) => (
                  <div
                    key={r.id}
                    className={cn(
                      'absolute border-2 rounded-sm transition-colors',
                      editingId === r.id
                        ? 'border-status-info-border bg-status-info-solid'
                        : r.isGlobalNav
                          ? 'border-status-accent-border bg-status-accent-solid'
                          : 'border-status-success-border bg-status-success-solid',
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
                    className="absolute border-2 border-status-info-border bg-status-info-solid rounded-sm"
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
          <div className="flex min-h-0 w-full shrink-0 flex-col border-t lg:w-80 lg:border-t-0 lg:border-l">
            <ScrollArea className="flex-1 p-4">
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <h4 className="text-sm font-semibold">标注列表 ({regions.length})</h4>
                  <div className="flex items-center gap-2">
                    <Button
                      variant="secondary"
                      size="sm"
                      className="text-xs"
                      onClick={addKeyboardRegion}
                    >
                      <Plus className="size-3.5" aria-hidden="true" />
                      新增标注
                    </Button>
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
                </div>

                {historyError && (
                  <p role="alert" className="rounded-md border border-destructive/40 bg-destructive/10 p-2 text-xs text-destructive">
                    {historyError}
                  </p>
                )}
                {regions.some((region) => region.coordinateStatus === 'missing') && (
                  <p role="alert" className="rounded-md border border-status-warning-border bg-status-warning-muted p-2 text-xs text-status-warning">
                    {regions.filter((region) => region.coordinateStatus === 'missing').length} 条旧标注缺少真实坐标，保存前必须重新定位。
                  </p>
                )}

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
                          ? 'border-status-info-border bg-status-info-muted'
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
                          aria-label={`删除标注区域 ${r.id.slice(-4)}`}
                        >
                          <Trash2 className="h-3 w-3" aria-hidden="true" />
                        </Button>
                      </div>

                      {editingId === r.id ? (
                        <>
                          <div>
                            <Label htmlFor={`target-page-${r.id}`} className="text-xs">目标页面</Label>
                            <Select
                              value={r.targetPage}
                              onValueChange={(v) =>
                                updateRegion(r.id, { targetPage: v })
                              }
                            >
                              <SelectTrigger id={`target-page-${r.id}`} className="h-8 text-xs">
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
                            <Label htmlFor={`interaction-type-${r.id}`} className="text-xs">交互类型</Label>
                            <Select
                              value={r.interactionType}
                              onValueChange={(v) =>
                                updateRegion(r.id, { interactionType: v })
                              }
                            >
                              <SelectTrigger id={`interaction-type-${r.id}`} className="h-8 text-xs">
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
                            <Label htmlFor={`source-element-${r.id}`} className="text-xs">触发元素</Label>
                            <Input
                              id={`source-element-${r.id}`}
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
                          <fieldset className="space-y-2 rounded-md border p-2">
                            <legend className="px-1 text-xs font-medium">真实截图坐标</legend>
                            {r.coordinateStatus === 'missing' && (
                              <p className="text-xs text-destructive">旧数据缺少有效坐标，请根据截图重新填写。</p>
                            )}
                            <div className="grid grid-cols-2 gap-2">
                              {([
                                ['x', 'X'],
                                ['y', 'Y'],
                                ['width', '宽度'],
                                ['height', '高度'],
                              ] as const).map(([field, label]) => (
                                <div key={field}>
                                  <Label htmlFor={`${field}-${r.id}`} className="text-xs">{label}</Label>
                                  <Input
                                    id={`${field}-${r.id}`}
                                    type="number"
                                    min={field === 'width' || field === 'height' ? 1 : 0}
                                    step="1"
                                    className="h-8 text-xs"
                                    value={r[field]}
                                    onChange={(event) => updateRegion(r.id, {
                                      [field]: Number(event.target.value),
                                    })}
                                  />
                                </div>
                              ))}
                            </div>
                          </fieldset>
                          {r.interactionType === 'dynamic_filter' && (
                            <div>
                              <Label htmlFor={`admin-source-${r.id}`} className="text-xs">运营后台配置源</Label>
                              <Input
                                id={`admin-source-${r.id}`}
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
                            <span className="font-medium text-status-info">
                              {r.targetPage || '未设置'}
                            </span>
                          </p>
                          <Badge tone="neutral" className="text-xs">
                            {INTERACTION_TYPES.find(
                              (t) => t.value === r.interactionType,
                            )?.label ?? r.interactionType}
                          </Badge>
                          {r.isGlobalNav && (
                            <Badge className="text-xs ml-1 bg-status-accent-muted text-status-accent">
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
                variant="primary"
                size="sm"
                className="flex-1"
                onClick={handleSave}
                disabled={saving || regions.length === 0}
              >
                {saving ? '保存中...' : '保存'}
              </Button>
              <Button
                variant="secondary"
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
