import { useState, useEffect, useCallback } from 'react'
import { fetchModule } from '@/api/requirementModules'
import { fetchGlobalNav } from '@/api/requirementModules'
import type { ModuleTreeNode, GlobalNavItemOut } from '@/types'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from '@/components/ui/sheet'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Separator } from '@/components/ui/separator'
import {
  ArrowRight,
  ArrowLeft,
  Globe,
  ExternalLink,
  Focus,
  type LucideIcon,
} from '@/lib/icons'
import { cn } from '@/lib/utils'

interface PageInteraction {
  trigger: string
  target_page: string
  interaction_type: string
  source_element?: string
  admin_config_source?: string
}

interface PageInteractionPanelProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  page: ModuleTreeNode | null
  bundleId: number
  onAnnotate?: (page: ModuleTreeNode) => void
}

const INTERACTION_LABELS: Record<string, string> = {
  navigation: '页面跳转',
  modal: '弹窗',
  tab_switch: 'Tab 切换',
  external: '外链',
  dynamic_filter: '动态筛选',
  global_navigation: '全局导航',
}

const INTERACTION_ICONS: Record<string, LucideIcon> = {
  navigation: ArrowRight,
  modal: ExternalLink,
  tab_switch: ExternalLink,
  external: ExternalLink,
  dynamic_filter: ExternalLink,
  global_navigation: Globe,
}

export default function PageInteractionPanel({
  open,
  onOpenChange,
  page,
  bundleId,
  onAnnotate,
}: PageInteractionPanelProps) {
  const [interactions, setInteractions] = useState<PageInteraction[]>([])
  const [globalNav, setGlobalNav] = useState<GlobalNavItemOut[]>([])
  const [loading, setLoading] = useState(false)

  const parseData = useCallback(async () => {
    if (!page || !open) return

    setLoading(true)
    try {
      // Load full module detail for interactions
      const detail = await fetchModule(page.id)
      setInteractions(
        JSON.parse(detail.page_interactions || '[]') as PageInteraction[],
      )

      // Load global nav
      const nav = await fetchGlobalNav(bundleId)
      setGlobalNav(nav.filter((n) => n.target_page === page.name))
    } catch {
      // Fallback: parse from tree node
      try {
        setInteractions(JSON.parse(page.page_interactions || '[]') as PageInteraction[])
      } catch {
        setInteractions([])
      }
    } finally {
      setLoading(false)
    }
  }, [page, open, bundleId])

  useEffect(() => {
    parseData()
  }, [parseData])

  const outgoing = interactions.filter(
    (ia) => ia.interaction_type !== 'global_navigation',
  )
  const globalNavItems = [
    ...interactions.filter((ia) => ia.interaction_type === 'global_navigation'),
  ]

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="w-[400px] sm:w-[540px] p-0">
        <SheetHeader className="p-6 pb-2">
          <SheetTitle className="text-lg flex items-center gap-2">
            {page?.name ?? '页面交互'}
          </SheetTitle>
          <SheetDescription>
            {page?.platform ? `${page.platform} 端 · ` : ''}页面跳转关系
          </SheetDescription>
        </SheetHeader>

        <ScrollArea className="h-[calc(100vh-120px)] px-6 pb-6">
          {loading ? (
            <div className="space-y-4">
              <Skeleton className="h-24 w-full" />
              <Skeleton className="h-24 w-full" />
              <Skeleton className="h-24 w-full" />
            </div>
          ) : (
            <div className="space-y-6">
              {/* Outgoing Navigation */}
              <Section
                title="出向导航"
                icon={ArrowRight}
                count={outgoing.length}
              >
                {outgoing.length === 0 ? (
                  <EmptyHint>暂无出向导航</EmptyHint>
                ) : (
                  outgoing.map((ia, i) => (
                    <InteractionRow key={i} interaction={ia} />
                  ))
                )}
              </Section>

              <Separator />

              {/* Incoming Navigation — placeholder */}
              <Section
                title="入向导航"
                icon={ArrowLeft}
                count={0}
              >
                <EmptyHint>入向导航需跨页面扫描</EmptyHint>
              </Section>

              <Separator />

              {/* Global Navigation */}
              <Section
                title="全局导航"
                icon={Globe}
                count={globalNavItems.length + globalNav.length}
              >
                {globalNavItems.length === 0 && globalNav.length === 0 ? (
                  <EmptyHint>暂无全局导航标记</EmptyHint>
                ) : (
                  <>
                    {globalNavItems.map((ia, i) => (
                      <InteractionRow key={`gn-${i}`} interaction={ia} />
                    ))}
                    {globalNav.map((gn, i) => (
                      <div
                        key={`gn-ext-${i}`}
                        className="flex items-center gap-2 p-2 rounded-md bg-purple-50 dark:bg-purple-950 text-sm"
                      >
                        <Globe className="h-4 w-4 text-purple-500 shrink-0" />
                        <span className="flex-1">{gn.trigger}</span>
                        <Badge className="text-xs bg-purple-100 text-purple-700 dark:bg-purple-900 dark:text-purple-300">
                          全局导航
                        </Badge>
                        <span className="text-xs text-muted-foreground">
                          覆盖率 {(gn.coverage * 100).toFixed(0)}%
                        </span>
                      </div>
                    ))}
                  </>
                )}
              </Section>

              {/* Annotate button */}
              {onAnnotate && page && (
                <div className="pt-2">
                  <Button
                    variant="outline"
                    className="w-full"
                    onClick={() => onAnnotate(page)}
                  >
                    <Focus className="h-4 w-4 mr-2" />
                    标注截图交互
                  </Button>
                </div>
              )}
            </div>
          )}
        </ScrollArea>
      </SheetContent>
    </Sheet>
  )
}

function Section({
  title,
  icon: Icon,
  count,
  children,
}: {
  title: string
  icon: LucideIcon
  count: number
  children: React.ReactNode
}) {
  return (
    <div>
      <div className="flex items-center gap-2 mb-2">
        <Icon className="h-4 w-4 text-muted-foreground" />
        <h4 className="text-sm font-semibold">{title}</h4>
        {count > 0 && (
          <Badge variant="secondary" className="text-xs">
            {count}
          </Badge>
        )}
      </div>
      <div className="space-y-1.5">{children}</div>
    </div>
  )
}

function EmptyHint({ children }: { children: React.ReactNode }) {
  return (
    <p className="text-xs text-muted-foreground py-2 text-center">{children}</p>
  )
}

function InteractionRow({ interaction: ia }: { interaction: PageInteraction }) {
  const typeLabel =
    INTERACTION_LABELS[ia.interaction_type] ?? ia.interaction_type
  const isDynamic = ia.interaction_type === 'dynamic_filter'
  const isGlobalNav = ia.interaction_type === 'global_navigation'

  return (
    <div
      className={cn(
        'flex items-start gap-2 p-2.5 rounded-md border text-sm',
        isDynamic && 'border-purple-200 bg-purple-50/50 dark:bg-purple-950/50',
        isGlobalNav && 'border-purple-200 bg-purple-50/50 dark:bg-purple-950/50',
        !isDynamic && !isGlobalNav && 'bg-muted/30',
      )}
    >
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="font-medium truncate">
            {ia.trigger || '未命名'}
          </span>
          <ArrowRight className="h-3 w-3 text-muted-foreground shrink-0" />
          <span className="font-medium text-blue-600 truncate">
            {ia.target_page || '未知页面'}
          </span>
        </div>
        {ia.source_element && (
          <p className="text-xs text-muted-foreground mt-0.5">
            元素: {ia.source_element}
          </p>
        )}
        {ia.admin_config_source && (
          <p className="text-xs text-purple-600 mt-0.5">
            运营后台配置: {ia.admin_config_source}
          </p>
        )}
      </div>
      <Badge
        className={cn(
          'text-xs shrink-0',
          isDynamic
            ? 'bg-purple-100 text-purple-700 dark:bg-purple-900 dark:text-purple-300'
            : isGlobalNav
              ? 'bg-purple-100 text-purple-700 dark:bg-purple-900 dark:text-purple-300'
              : 'bg-blue-100 text-blue-700',
        )}
      >
        {typeLabel}
      </Badge>
    </div>
  )
}
