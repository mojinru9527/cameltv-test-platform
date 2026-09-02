import {
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarMenuSub,
  SidebarMenuSubButton,
  SidebarMenuSubItem,
} from '@/components/ui/sidebar'
import type { MainNavRow } from './nav-config'
import { menuIcon } from './NavigationMenuItems'

function isActivePath(pathname: string, path: string): boolean {
  return pathname === path || (path !== '/' && pathname.startsWith(path))
}

/**
 * batch-212（B2）顶层 5 行渲染：链接行（工作台/知识中心）与分组行
 * （版本验收/结果与缺陷，组头不可点击，children 常显）。由 MainLayout 使用。
 */
export function MainNavRows({
  rows,
  pathname,
  onNavigate,
}: {
  rows: MainNavRow[]
  pathname: string
  onNavigate: (path: string, label: string) => void
}) {
  return (
    <>
      {rows.map((row) => {
        if (row.kind === 'link') {
          const Icon = menuIcon(row.item.icon)
          const active = isActivePath(pathname, row.item.path)
          return (
            <SidebarMenuItem key={row.item.code}>
              <SidebarMenuButton
                onClick={() => onNavigate(row.item.path, row.item.name)}
                isActive={active}
                aria-current={active ? 'page' : undefined}
                tooltip={row.item.name}
              >
                <Icon aria-hidden="true" />
                <span>{row.item.name}</span>
              </SidebarMenuButton>
            </SidebarMenuItem>
          )
        }
        return (
          <SidebarMenuItem key={row.label} className="flex flex-col items-stretch">
            <div
              className="px-2 pt-2 text-xs font-semibold text-sidebar-foreground/60"
              aria-hidden="true"
            >
              {row.label}
            </div>
            <SidebarMenuSub>
              {row.items.map((child) => {
                const ChildIcon = menuIcon(child.icon)
                const active = isActivePath(pathname, child.path)
                return (
                  <SidebarMenuSubItem key={child.code || child.path}>
                    <SidebarMenuSubButton
                      onClick={() => onNavigate(child.path, child.name)}
                      isActive={active}
                      aria-current={active ? 'page' : undefined}
                    >
                      <ChildIcon className="size-3.5" aria-hidden="true" />
                      <span>{child.name}</span>
                    </SidebarMenuSubButton>
                  </SidebarMenuSubItem>
                )
              })}
            </SidebarMenuSub>
          </SidebarMenuItem>
        )
      })}
    </>
  )
}