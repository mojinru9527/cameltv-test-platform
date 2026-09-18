import { useState } from 'react'
import {
  SidebarGroup,
  SidebarGroupLabel,
  SidebarMenu,
  useSidebar,
} from '@/ui'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/ui'
import { ChevronRight } from '@/lib/icons'
import type { ExpertSection } from './nav-config'
import { isPathInItems, readAssetsMoreOpen, writeAssetsMoreOpen } from './nav-config'
import { NavigationMenuItems } from './NavigationMenuItems'

/**
 * 「专家区」折叠容器（batch-259 / B2-6 收敛后的二级区域）。
 * 文件名为 batch-212 历史遗留（当时叫「资产与更多」）；用户可见名称是 **专家区**，
 * 它不占一级入口额度（`PRIMARY_ENTRY_LIMIT`），而是二级容器 + 权限门禁。
 * 模块按 资产/引擎与配置/个人/系统 分桶收进这里（空分桶/空容器不渲染），
 * 展开状态持久化到 localStorage；当前页落在任一桶内时自动展开。
 * 侧边栏图标折叠模式（collapsible="icon"）下不做折叠组，分桶项直接图标平铺。
 */
export function AssetsMoreGroup({
  sections,
  pathname,
  onNavigate,
}: {
  sections: ExpertSection[]
  pathname: string
  onNavigate: (path: string, label: string) => void
}) {
  const { state, isMobile } = useSidebar()
  const [open, setOpen] = useState<boolean>(() => readAssetsMoreOpen(window.localStorage))
  const total = sections.reduce((sum, section) => sum + section.items.length, 0)
  const containsActive = sections.some((section) => isPathInItems(pathname, section.items))
  const effectiveOpen = open || containsActive
  const iconCollapsed = state === 'collapsed' && !isMobile

  if (sections.length === 0) return null

  if (iconCollapsed) {
    // 图标折叠模式：分桶项以图标平铺（tooltip 展示名称）
    return (
      <SidebarGroup>
        <SidebarMenu>
          {sections.map((section) => (
            <NavigationMenuItems
              key={section.label}
              items={section.items}
              pathname={pathname}
              onNavigate={onNavigate}
            />
          ))}
        </SidebarMenu>
      </SidebarGroup>
    )
  }

  const onOpenChange = (next: boolean) => {
    setOpen(next)
    writeAssetsMoreOpen(window.localStorage, next)
  }

  return (
    <Collapsible open={effectiveOpen} onOpenChange={onOpenChange} className="group/assets">
      <SidebarGroup>
        <SidebarGroupLabel asChild>
          <CollapsibleTrigger className="flex w-full items-center justify-between">
            <span>专家区</span>
            <span className="flex items-center gap-1">
              <span className="text-xs opacity-60">{total}</span>
              <ChevronRight
                className="size-3.5 transition-transform group-data-[state=open]/assets:rotate-90"
                aria-hidden="true"
              />
            </span>
          </CollapsibleTrigger>
        </SidebarGroupLabel>
        <CollapsibleContent>
          {sections.map((section) => (
            <div key={section.label} className="space-y-0.5">
              <div
                className="px-2 pt-2 text-xs font-semibold text-sidebar-foreground/60"
                aria-hidden="true"
              >
                {section.label}
              </div>
              <SidebarMenu>
                <NavigationMenuItems
                  items={section.items}
                  pathname={pathname}
                  onNavigate={onNavigate}
                />
              </SidebarMenu>
            </div>
          ))}
        </CollapsibleContent>
      </SidebarGroup>
    </Collapsible>
  )
}
