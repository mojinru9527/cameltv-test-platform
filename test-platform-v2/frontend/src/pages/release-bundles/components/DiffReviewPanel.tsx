import { useState } from 'react'
import { toast } from 'sonner'
import { confirmVersionDiff } from '@/api/releaseBundles'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'
import {
  ChevronRight,
  CheckCircle2,
  XCircle,
  FileText,
} from '@/lib/icons'
import { cn } from '@/lib/utils'
import type { VersionDiffResult } from '@/types'

interface ReviewModule {
  id: string
  name: string
  change_type: 'new' | 'modified' | 'deleted' | 'unchanged'
  pages: DiffPage[]
}

interface DiffPage {
  name: string
  change_type: 'new' | 'modified' | 'deleted' | 'unchanged'
  old_name?: string
  new_name?: string
  detail?: string
}

interface DiffReviewPanelProps {
  bundleId: number
  diffResult: VersionDiffResult | null
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
  const [expandedModules, setExpandedModules] = useState<Set<string>>(new Set())
  const [overrides, setOverrides] = useState<
    Record<string, { action: 'confirm' | 'reject' }>
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

  if (!diffResult) {
    return (
      <div className="flex min-h-48 items-center justify-center text-sm text-muted-foreground">
        {loading ? "正在加载版本差异…" : "暂无版本差异数据"}
      </div>
    )
  }

  const data = diffResult
  const modules: ReviewModule[] = [
    ...data.new_modules.map((name) => ({
      id: `new:${name}`,
      name,
      change_type: 'new' as const,
      pages: [],
    })),
    ...data.modified_modules.map((module) => ({
      id: `modified:${module.module_name}`,
      name: module.module_name,
      change_type: 'modified' as const,
      pages: [
        ...module.new_pages.map((name) => ({ name, change_type: 'new' as const })),
        ...module.modified_pages.map((name) => ({ name, change_type: 'modified' as const })),
        ...module.deleted_pages.map((name) => ({ name, change_type: 'deleted' as const })),
        ...module.unchanged_pages.map((name) => ({ name, change_type: 'unchanged' as const })),
      ],
    })),
    ...data.deleted_modules.map((name) => ({
      id: `deleted:${name}`,
      name,
      change_type: 'deleted' as const,
      pages: [],
    })),
    ...data.unchanged_modules.map((name) => ({
      id: `unchanged:${name}`,
      name,
      change_type: 'unchanged' as const,
      pages: [],
    })),
  ]
  const totalModules = modules.length
  const totalPages = modules.reduce((count, module) => count + module.pages.length, 0)
  const summary = {
    new_modules: data.new_modules.length,
    modified_modules: data.modified_modules.length,
    deleted_modules: data.deleted_modules.length,
    unchanged_modules: data.unchanged_modules.length,
  }

  // Group modules by change_type
  const grouped: Record<string, ReviewModule[]> = {}
  for (const zone of CHANGE_ZONES) {
    grouped[zone.key] = modules.filter((m) => m.change_type === zone.key)
  }

  const toggleModule = (id: string) => {
    setExpandedModules((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const setOverride = (moduleId: string, action: 'confirm' | 'reject') => {
    setOverrides((prev) => ({
      ...prev,
      [moduleId]: { action },
    }))
  }

  const handleConfirmAll = async () => {
    setConfirming(true)
    try {
      const skipModules = modules
        .filter((module) => overrides[module.id]?.action === 'reject')
        .map((module) => module.name)
      const result = await confirmVersionDiff(bundleId, {
        overrides: { skip_modules: skipModules },
      })
      toast.success(`差异已确认，已构建 ${result.created_modules} 个节点`)
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
                {totalModules} 模块 · {totalPages} 个页面变化 · 置信度 {Math.round(data.diff_confidence * 100)}%
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
                        {mod.pages.map((page, idx) => (
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
                            <CheckCircle2 className="h-3 w-3 mr-1" /> 接受
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
                            <XCircle className="h-3 w-3 mr-1" /> 跳过
                          </Button>
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
        </div>
      )}
    </div>
  )
}
