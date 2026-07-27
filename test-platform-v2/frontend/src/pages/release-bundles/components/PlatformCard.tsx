import { useState } from 'react'
import type { ModuleTreeNode } from '@/types'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'
import { ChevronRight, Smartphone, Monitor, Globe, Shield, Package, type LucideIcon } from '@/lib/icons'
import { cn } from '@/lib/utils'

const PLATFORM_ICONS: Record<string, LucideIcon> = {
  APP: Smartphone,
  PC: Monitor,
  WEB: Globe,
  ADMIN: Shield,
}

const PLATFORM_LABELS: Record<string, string> = {
  APP: 'APP 端',
  PC: 'PC 端',
  WEB: 'WEB 端',
  ADMIN: '运营后台',
}

const CHANGE_BADGE: Record<string, { className: string; label: string }> = {
  new: { className: 'bg-green-100 text-green-700 border-green-200', label: '新增' },
  modified: { className: 'bg-yellow-100 text-yellow-700 border-yellow-200', label: '修改' },
  deleted: { className: 'bg-red-100 text-red-700 border-red-200', label: '删除' },
  unchanged: { className: 'bg-gray-100 text-gray-500 border-gray-200', label: '未变更' },
}

interface PageInteraction {
  trigger: string
  target_page: string
  interaction_type: string
  source_element?: string
  admin_config_source?: string
}

interface PlatformCardProps {
  platform: string
  modules: ModuleTreeNode[]
  onPageClick?: (page: ModuleTreeNode) => void
}

function parseInteractions(interactionsJson: string): PageInteraction[] {
  try {
    return JSON.parse(interactionsJson || '[]')
  } catch {
    return []
  }
}

function PageItem({
  page,
  onPageClick,
}: {
  page: ModuleTreeNode
  onPageClick?: (page: ModuleTreeNode) => void
}) {
  const interactions = parseInteractions(page.page_interactions)
  const outgoing = interactions.filter(
    (ia) => ia.interaction_type !== 'global_navigation',
  ).length
  const incoming = 0 // incoming requires cross-page lookup
  const hasDynamicFilter = interactions.some(
    (ia) => ia.interaction_type === 'dynamic_filter',
  )

  const changeConfig = CHANGE_BADGE[page.change_type] ?? CHANGE_BADGE.unchanged

  return (
    <div
      className={cn(
        'flex items-center pl-8 pr-2 py-1.5 hover:bg-accent rounded-sm cursor-pointer text-sm group',
      )}
      onClick={() => onPageClick?.(page)}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') onPageClick?.(page)
      }}
    >
      <span className="truncate flex-1">{page.name}</span>
      <div className="flex items-center gap-1 shrink-0">
        <Badge variant="outline" className={cn('text-xs px-1 py-0', changeConfig.className)}>
          {changeConfig.label}
        </Badge>
        {outgoing > 0 && (
          <Badge variant="secondary" className="text-xs px-1 py-0">
            →{outgoing}
          </Badge>
        )}
        {hasDynamicFilter && (
          <Badge className="text-xs px-1 py-0 bg-purple-100 text-purple-700 dark:bg-purple-900 dark:text-purple-300">
            动态筛选
          </Badge>
        )}
      </div>
    </div>
  )
}

function ModuleCard({
  module: mod,
  onPageClick,
}: {
  module: ModuleTreeNode
  onPageClick?: (page: ModuleTreeNode) => void
}) {
  const [open, setOpen] = useState(true)

  return (
    <Collapsible open={open} onOpenChange={setOpen}>
      <CollapsibleTrigger asChild>
        <button
          className={cn(
            'flex items-center w-full p-2 hover:bg-muted rounded-md text-left',
            'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
          )}
        >
          <ChevronRight
            className={cn(
              'h-4 w-4 shrink-0 transition-transform duration-200',
              open && 'rotate-90',
            )}
          />
          <span className="font-medium text-sm ml-2 truncate">{mod.name}</span>
          <Badge variant="outline" className="ml-auto text-xs shrink-0">
            {mod.child_count ?? mod.children?.length ?? 0} 页
          </Badge>
        </button>
      </CollapsibleTrigger>
      <CollapsibleContent>
        <div className="ml-2 border-l border-border">
          {mod.children?.map((page) => (
            <PageItem key={page.id} page={page} onPageClick={onPageClick} />
          ))}
          {(!mod.children || mod.children.length === 0) && (
            <div className="pl-8 py-2 text-xs text-muted-foreground">
              暂无页面
            </div>
          )}
        </div>
      </CollapsibleContent>
    </Collapsible>
  )
}

export default function PlatformCard({
  platform,
  modules,
  onPageClick,
}: PlatformCardProps) {
  const Icon = PLATFORM_ICONS[platform] ?? Package

  return (
    <Card className="flex-1 min-w-0">
      <CardHeader className="pb-2">
        <div className="flex items-center gap-2">
          <Icon className="h-5 w-5 text-muted-foreground" />
          <CardTitle className="text-base">
            {PLATFORM_LABELS[platform] ?? platform}
          </CardTitle>
          <Badge variant="secondary" className="text-xs">
            {modules.length} 模块
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-0.5">
        {modules.length === 0 ? (
          <p className="text-sm text-muted-foreground text-center py-4">
            暂无模块数据
          </p>
        ) : (
          modules.map((mod) => (
            <ModuleCard key={mod.id} module={mod} onPageClick={onPageClick} />
          ))
        )}
      </CardContent>
    </Card>
  )
}

// Re-export for use in VersionPanorama
export { PLATFORM_ICONS, PLATFORM_LABELS }
