import { useState } from 'react'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { cn } from '@/lib/utils'

interface ModuleVersionChange {
  version: string
  release_date?: string
  changes: {
    type: 'new' | 'modified' | 'deleted'
    pageName: string
    detail?: string
  }[]
}

interface ModuleTimelineProps {
  moduleName: string
  versions?: ModuleVersionChange[]
  loading?: boolean
}

const CHANGE_COLORS: Record<string, { dot: string; line: string; badge: string; label: string }> = {
  new: {
    dot: 'bg-green-500',
    line: 'border-green-200 bg-green-50/30',
    badge: 'bg-green-100 text-green-700',
    label: '新增',
  },
  modified: {
    dot: 'bg-yellow-500',
    line: 'border-yellow-200 bg-yellow-50/30',
    badge: 'bg-yellow-100 text-yellow-700',
    label: '修改',
  },
  deleted: {
    dot: 'bg-red-500',
    line: 'border-red-200 bg-red-50/30',
    badge: 'bg-red-100 text-red-700',
    label: '删除',
  },
}

export default function ModuleTimeline({
  moduleName,
  versions = [],
  loading = false,
}: ModuleTimelineProps) {
  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base">模块演化: {moduleName}</CardTitle>
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className="space-y-4">
            {[1, 2, 3].map((i) => (
              <div key={i} className="flex gap-3">
                <Skeleton className="h-4 w-4 rounded-full shrink-0 mt-1" />
                <div className="flex-1 space-y-2">
                  <Skeleton className="h-4 w-24" />
                  <Skeleton className="h-10 w-full" />
                </div>
              </div>
            ))}
          </div>
        ) : versions.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground">
            <p className="text-sm">暂无演化记录</p>
            <p className="text-xs mt-1">该模块仅存在于当前版本</p>
          </div>
        ) : (
          <div className="relative">
            {/* Vertical line */}
            <div className="absolute left-[7px] top-2 bottom-2 w-0.5 bg-border" />

            <div className="space-y-6">
              {versions.map((v, vi) => (
                <div key={vi} className="relative pl-8">
                  {/* Dot */}
                  <div className="absolute left-0 top-1.5 w-[15px] h-[15px] rounded-full border-2 border-background bg-primary z-10" />
                  <div className="absolute left-[3px] top-[6px] w-[9px] h-[9px] rounded-full bg-background z-20" />

                  {/* Version header */}
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-sm font-semibold">{v.version}</span>
                    {vi === 0 && (
                      <Badge variant="outline" className="text-xs border-primary/30 text-primary">
                        当前
                      </Badge>
                    )}
                    {v.release_date && (
                      <span className="text-xs text-muted-foreground">
                        {v.release_date}
                      </span>
                    )}
                  </div>

                  {/* Changes */}
                  {v.changes.length === 0 ? (
                    <p className="text-xs text-muted-foreground pl-1">
                      无变更
                    </p>
                  ) : (
                    <div className="space-y-1.5">
                      {v.changes.map((ch, ci) => (
                        <div
                          key={ci}
                          className={cn(
                            'flex items-center gap-2 p-2 rounded-md border-l-2 text-sm',
                            CHANGE_COLORS[ch.type]?.line ?? 'border-muted',
                          )}
                        >
                          <Badge
                            className={cn(
                              'text-xs px-1 py-0',
                              CHANGE_COLORS[ch.type]?.badge ?? '',
                            )}
                          >
                            {ch.type === 'new' ? '+' : ch.type === 'deleted' ? '−' : '~'}
                          </Badge>
                          <span className="flex-1 truncate">{ch.pageName}</span>
                          {ch.detail && (
                            <span className="text-xs text-muted-foreground truncate">
                              {ch.detail}
                            </span>
                          )}
                          <Badge variant="outline" className="text-xs">
                            {CHANGE_COLORS[ch.type]?.label ?? ch.type}
                          </Badge>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
