import {
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarMenuSub,
  SidebarMenuSubButton,
  SidebarMenuSubItem,
  useSidebar,
} from '@/components/ui/sidebar'
import type { MenuItem } from '@/types'
import {
  LayoutDashboard,
  FileText,
  FolderOpen,
  Clock,
  Bug,
  BarChart3,
  Settings,
  GitBranch,
  Share2,
  Sparkles,
  Cpu,
  Terminal,
  Database,
  Link2,
  Bell,
  Globe,
  type LucideIcon,
} from '@/lib/icons'

// Backend menu icon string → lucide-react component
const ICONS: Record<string, LucideIcon> = {
  DashboardOutlined: LayoutDashboard,
  NodeIndexOutlined: GitBranch,
  ShareAltOutlined: Share2,
  FileTextOutlined: FileText,
  ProfileOutlined: FolderOpen,
  ScheduleOutlined: Clock,
  ApiOutlined: FileText,
  RobotOutlined: FileText,
  PlayCircleOutlined: FileText,
  ClockCircleOutlined: Clock,
  BarChartOutlined: BarChart3,
  SettingOutlined: Settings,
  AppstoreOutlined: LayoutDashboard,
  BugOutlined: Bug,
  DatabaseOutlined: Database,
  LinkOutlined: Link2,
  NotificationOutlined: Bell,
  EnvironmentOutlined: Globe,
  BrainCircuitOutlined: Sparkles,
  SparklesOutlined: Sparkles,
  TerminalOutlined: Terminal,
  GitBranchOutlined: GitBranch,
  FolderOpenOutlined: FolderOpen,
  CpuOutlined: Cpu,
}

/** 侧边栏菜单项列表（含子项渲染）。由 MainLayout 与 MoreMenusGroup 共用。 */

/** 后端菜单 icon 字符串 → lucide 组件（batch-212 供顶层/分桶导航共用）。 */
export function menuIcon(icon: string): LucideIcon {
  return ICONS[icon] ?? LayoutDashboard
}

export function NavigationMenuItems({
  items,
  pathname,
  onNavigate,
}: {
  items: MenuItem[]
  pathname: string
  onNavigate: (path: string, label: string) => void
}) {
  const { isMobile, setOpenMobile } = useSidebar()

  const goTo = (path: string, label: string) => {
    onNavigate(path, label)
    if (isMobile) setOpenMobile(false)
  }

  return items.map((m) => {
    const Icon = ICONS[m.icon] ?? LayoutDashboard
    const isActive = pathname === m.path || (m.path !== '/' && pathname.startsWith(m.path))
    const hasChildren = m.children && m.children.length > 0

    if (hasChildren) {
      return (
        <SidebarMenuItem key={m.path || m.code}>
          <SidebarMenuButton
            onClick={() => goTo(m.path, m.name)}
            isActive={isActive}
            aria-current={isActive ? 'page' : undefined}
            tooltip={m.name}
            className="peer/menu-parent"
          >
            <Icon aria-hidden="true" />
            <span>{m.name}</span>
          </SidebarMenuButton>
          <SidebarMenuSub>
            {m.children!.map((child) => {
              const ChildIcon = ICONS[child.icon] ?? LayoutDashboard
              const childActive =
                pathname === child.path ||
                (child.path !== '/' && pathname.startsWith(child.path))
              return (
                <SidebarMenuSubItem key={child.path || child.code}>
                  <SidebarMenuSubButton
                    onClick={() => goTo(child.path, child.name)}
                    isActive={childActive}
                    aria-current={childActive ? 'page' : undefined}
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
    }

    return (
      <SidebarMenuItem key={m.path || m.code}>
        <SidebarMenuButton
          onClick={() => goTo(m.path, m.name)}
          isActive={isActive}
          aria-current={isActive ? 'page' : undefined}
          tooltip={m.name}
        >
          <Icon aria-hidden="true" />
          <span>{m.name}</span>
        </SidebarMenuButton>
      </SidebarMenuItem>
    )
  })
}
