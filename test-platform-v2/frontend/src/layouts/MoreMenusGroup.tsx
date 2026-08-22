import { useState } from 'react'
import {
  SidebarGroup,
  SidebarGroupLabel,
  SidebarMenu,
  useSidebar,
} from '@/components/ui/sidebar'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'
import { ChevronRight } from '@/lib/icons'
import type { MenuItem } from '@/types'
import { NavigationMenuItems } from './NavigationMenuItems'
import { isPathInMenus, readMoreMenusOpen, writeMoreMenusOpen } from './nav-config'

/**
 * (c165-3 导航频率分层)「更多功能」折叠组：低频一级菜单默认收起，
 * 展开状态持久化到 localStorage；当前页落在组内时强制展开，
 * 避免活跃导航项被折叠隐藏。
 * 侧边栏图标折叠模式（collapsible="icon"）下不做折叠组，低频项直接图标平铺。
 */
export function MoreMenusGroup({
  items,
  pathname,
  onNavigate,
}: {
  items: MenuItem[]
  pathname: string
  onNavigate: (path: string, label: string) => void
}) {
  const { state, isMobile } = useSidebar()
  const [open, setOpen] = useState<boolean>(() => readMoreMenusOpen(window.localStorage))
  const containsActive = isPathInMenus(pathname, items)
  const effectiveOpen = open || containsActive
  const iconCollapsed = state === 'collapsed' && !isMobile

  if (items.length === 0) return null

  if (iconCollapsed) {
    // 图标折叠模式：低频项以图标平铺（SidebarMenuButton tooltip 展示名称）
    return (
      <SidebarGroup>
        <SidebarMenu>
          <NavigationMenuItems items={items} pathname={pathname} onNavigate={onNavigate} />
        </SidebarMenu>
      </SidebarGroup>
    )
  }

  const onOpenChange = (next: boolean) => {
    setOpen(next)
    writeMoreMenusOpen(window.localStorage, next)
  }

  return (
    <Collapsible open={effectiveOpen} onOpenChange={onOpenChange} className="group/more">
      <SidebarGroup>
        <SidebarGroupLabel asChild>
          <CollapsibleTrigger className="flex w-full items-center justify-between">
            <span>更多功能</span>
            <span className="flex items-center gap-1">
              <span className="text-xs opacity-60">{items.length}</span>
              <ChevronRight
                className="size-3.5 transition-transform group-data-[state=open]/more:rotate-90"
                aria-hidden="true"
              />
            </span>
          </CollapsibleTrigger>
        </SidebarGroupLabel>
        <CollapsibleContent>
          <SidebarMenu>
            <NavigationMenuItems items={items} pathname={pathname} onNavigate={onNavigate} />
          </SidebarMenu>
        </CollapsibleContent>
      </SidebarGroup>
    </Collapsible>
  )
}
