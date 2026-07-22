import { useState } from 'react'
import { toast } from 'sonner'
import { confirmVersionDiff } from '@/api/releaseBundles'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { Textarea } from '@/components/ui/textarea'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'
import {
  ChevronRight,
  CheckCircle2,
  XCircle,
  FileDown,
  FileText,
} from '@/lib/icons'
import { cn } from '@/lib/utils'

interface DiffModule {
  id: number
  name: string
  platform: string
  change_type: 'new' | 'modified' | 'deleted' | 'unchanged'
  pages?: DiffPage[]
  changes?: string[]
}

interface DiffPage {
  name: string
  change_type: 'new' | 'modified' | 'deleted' | 'unchanged'
  old_name?: string
  new_name?: string
  detail?: string
}

interface DiffResult {
  summary?: {
    new_modules?: number
    modified_modules?: number
    deleted_modules?: number
    unchanged_modules?: number
    new_pages?: number
    modified_pages?: number
    deleted_pages?: number
  }
  modules?: DiffModule[]
  total_modules?: number
  total_pages?: number
}

interface DiffReviewPanelProps {
  bundleId: number
  diffResult: Record<string, unknown> | null
  onConfirm?: () => void
  loading?: boolean
}

const CHANGE_ZONES: { key: string; label: string; color: string }[] = [
  { key: 'new', label: '新增', color: 'border-l-green-500 bg-green-50/30' },
  { key: 'modified', label: '修改', color: 'border-l-yellow-500 bg-yellow-50/30' },
  { key: 'deleted', label: '删除', color: 'border-l-red-500 bg-red-50/30' },
  { key: 'unchanged', label: '未变更', color: 'border-l-muted' },
]

export default function DiffReviewPanel({
  bundleId,
  diffResult,
  onConfirm,
  loading = false,
}: DiffReviewPanelProps) {
  const [confirming, setConfirming] = useState(false)
  const [expandedModules, setExpandedModules] = useState<Set<number>>(new Set())
  const [overrides, setOverrides] = useState<
    Record<number, { action: string; comment: string }>
  >({})

  if (!diffResult && !loading) {
    return (
      <Card>
        <CardContent className="py-8 text-center text-muted-foreground">
          <FileText className="h-10 w-10 mx-auto mb-2 opacity-30" />
          <p>暂无差异数据</p>
          <p className="text-xs mt-1">请先在版本链 Tab 中触发版本差异分析</p>
        </CardContent>
      </Card>
    )
  }

  const data = (diffResult ?? {}) as DiffResult
  const summary = data.summary ?? {}
  const modules = data.modules ?? []
  const totalModules = data.total_modules ?? modules.length
  const totalPages = data.total_pages ?? 0

  // Group modules by change_type
  const grouped: Record<string, DiffModule[]> = {}
  for (const zone of CHANGE_ZONES) {
    grouped[zone.key] = modules.filter((m) => m.change_type === zone.key)
  }

  const toggleModule = (id: number) => {
    setExpandedModules((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const setOverride = (moduleId: number, action: string) => {
    setOverrides((prev) => ({
      ...prev,
      [moduleId]: { ...prev[moduleId], action, comment: prev[moduleId]?.comment ?? '' },
    }))
  }

  const setComment = (moduleId: number, comment: string) => {
    setOverrides((prev) => ({
      ...prev,
      [moduleId]: { ...prev[moduleId], action: prev[moduleId]?.action ?? '', comment },
    }))
  }

  const handleConfirmAll = async () => {
    setConfirming(true)
    try {
      const overrideEntries = Object.entries(overrides).map(
        ([id, { action, comment }]) => ({
          module_id: Number(id),
          action,
          comment,
        }),
      )
      await confirmVersionDiff(bundleId, {
        overrides: overrideEntries,
      })
      toast.success('差异已确认')
      onConfirm?.()
    } catch {
      toast.error('确认差异失败')
    } finally {
      setConfirming(false)
    }
  }

  return (
    <div className="space-y-4">
      {/* Summary Bar */}
      {loading ? (
        <Card>
          <CardContent className="py-4">
            <div className="flex gap-4">
              {[1, 2, 3, 4].map((i) => (
                <Skeleton key={i} className="h-8 w-20" />
              ))}
            </div>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardContent className="py-3">
            <div className="flex flex-wrap items-center gap-3">
              <span className="text-sm font-medium text-muted-foreground">
                差异总览:
              </span>
              <Badge
                variant="outline"
                className="border-green-200 bg-green-50 text-green-700"
              >
                新增 {summary.new_modules ?? 0}
              </Badge>
              <Badge
                variant="outline"
                className="border-yellow-200 bg-yellow-50 text-yellow-700"
              >
                修改 {summary.modified_modules ?? 0}
              </Badge>
              <Badge
                variant="outline"
                className="border-red-200 bg-red-50 text-red-700"
              >
                删除 {summary.deleted_modules ?? 0}
              </Badge>
              <Badge variant="outline" className="text-muted-foreground">
                未变更 {summary.unchanged_modules ?? 0}
              </Badge>
              <span className="text-xs text-muted-foreground ml-auto">
                {totalModules} 模块 · {totalPages} 页面
              </span>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Module Diff List */}
      {loading ? (
        <div className="space-y-2">
          {[1, 2, 3, 4, 5].map((i) => (
            <Skeleton key={i} className="h-16 w-full" />
          ))}
        </div>
      ) : (
        CHANGE_ZONES.map((zone) => {
          const zoneModules = grouped[zone.key] ?? []
          if (zoneModules.length === 0) return null

          return (
            <div key={zone.key} className="space-y-2">
              <h3 className="text-sm font-semibold text-muted-foreground px-1">
                {zone.label} ({zoneModules.length})
              </h3>
              {zoneModules.map((mod) => (
                <Collapsible
                  key={mod.id}
                  open={expandedModules.has(mod.id)}
                  onOpenChange={() => toggleModule(mod.id)}
                >
                  <div
                    className={cn(
                      'border border-l-4 rounded-md bg-card',
                      zone.color,
                    )}
                  >
                    <CollapsibleTrigger asChild>
                      <button
                        className={cn(
                          'flex items-center w-full p-3 text-left',
                          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded-md',
                        )}
                      >
                        <ChevronRight
                          className={cn(
                            'h-4 w-4 shrink-0 transition-transform duration-200',
                            expandedModules.has(mod.id) && 'rotate-90',
                          )}
                        />
                        <span className="font-medium text-sm ml-2 flex-1">
                          {mod.name}
                        </span>
                        <span className="text-xs text-muted-foreground mr-2">
                          {mod.platform}
                        </span>
                        <Badge
                          variant="outline"
                          className={cn(
                            'text-xs',
                            mod.change_type === 'new' &&
                              'border-green-200 text-green-700',
                            mod.change_type === 'modified' &&
                              'border-yellow-200 text-yellow-700',
                            mod.change_type === 'deleted' &&
                              'border-red-200 text-red-700',
                          )}
                        >
                          {zone.label}
                        </Badge>
                      </button>
                    </CollapsibleTrigger>
                    <CollapsibleContent>
                      <div className="px-3 pb-3 space-y-1">
                        {/* Page-level changes */}
                        {mod.pages?.map((page, idx) => (
                          <div
                            key={idx}
                            className="flex items-center gap-2 ml-6 py-1 text-sm"
                          >
                            <Badge
                              variant="outline"
                              className={cn(
                                'text-xs px-1',
                                page.change_type === 'new' &&
                                  'border-green-200 text-green-700',
                                page.change_type === 'modified' &&
                                  'border-yellow-200 text-yellow-700',
                                page.change_type === 'deleted' &&
                                  'border-red-200 text-red-700',
                              )}
                            >
                              {page.change_type === 'new'
                                ? '+'
                                : page.change_type === 'deleted'
                                  ? '−'
                                  : '~'}
                            </Badge>
                            <span className="truncate">{page.name}</span>
                            {page.detail && (
                              <span className="text-xs text-muted-foreground truncate">
                                ({page.detail})
                              </span>
                            )}
                          </div>
                        ))}

                        {/* Changes list (text-based) */}
                        {(!mod.pages || mod.pages.length === 0) &&
                          mod.changes?.map((ch, idx) => (
                            <div
                              key={idx}
                              className="flex items-center gap-2 ml-6 py-1 text-sm"
                            >
                              <span className="text-xs text-muted-foreground">
                                • {ch}
                              </span>
                            </div>
                          ))}

                        {/* Override controls */}
                        <div className="flex items-center gap-2 mt-3 ml-6 pt-2 border-t">
                          <span className="text-xs text-muted-foreground">
                            修正:
                          </span>
                          <Button
                            variant={
                              overrides[mod.id]?.action === 'confirm'
                                ? 'default'
                                : 'outline'
                            }
                            size="sm"
                            className="h-7 text-xs"
                            onClick={() => setOverride(mod.id, 'confirm')}
                          >
                            <CheckCircle2 className="h-3 w-3 mr-1" /> 确认
                          </Button>
                          <Button
                            variant={
                              overrides[mod.id]?.action === 'reject'
                                ? 'destructive'
                                : 'outline'
                            }
                            size="sm"
                            className="h-7 text-xs"
                            onClick={() => setOverride(mod.id, 'reject')}
                          >
                            <XCircle className="h-3 w-3 mr-1" /> 拒绝
                          </Button>
                          <Button
                            variant={
                              overrides[mod.id]?.action === 'correct'
                                ? 'secondary'
                                : 'outline'
                            }
                            size="sm"
                            className="h-7 text-xs"
                            onClick={() => setOverride(mod.id, 'correct')}
                          >
                            修正
                          </Button>
                          {overrides[mod.id]?.action === 'correct' && (
                            <Textarea
                              placeholder="修正说明..."
                              className="h-7 text-xs flex-1 min-h-0 py-1"
                              value={overrides[mod.id]?.comment ?? ''}
                              onChange={(e) =>
                                setComment(mod.id, e.target.value)
                              }
                            />
                          )}
                        </div>
                      </div>
                    </CollapsibleContent>
                  </div>
                </Collapsible>
              ))}
            </div>
          )
        })
      )}

      {/* Action Bar */}
      {!loading && modules.length > 0 && (
        <div className="flex items-center gap-2 pt-2">
          <Button onClick={handleConfirmAll} disabled={confirming}>
            <CheckCircle2 className="h-4 w-4 mr-1" />
            {confirming ? '确认中...' : '确认全部'}
          </Button>
          <Button variant="outline">
            <FileDown className="h-4 w-4 mr-1" />
            导出报告
          </Button>
        </div>
      )}
    </div>
  )
}
