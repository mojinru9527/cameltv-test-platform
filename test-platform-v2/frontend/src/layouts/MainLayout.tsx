import { useEffect, useState } from 'react'
import { Outlet, useLocation, useNavigate } from 'react-router-dom'
import { toast } from 'sonner'
import { fetchMenus, logoutApi } from '@/api/auth'
import { useAuthStore } from '@/stores/auth'
import type { ColorTheme } from '@/stores/auth'
import { useTheme } from '@/components/theme-provider'
import { COLOR_THEMES, getThemeDefinition } from '@/lib/themes'
import type { MenuItem } from '@/types'
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarInset,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarMenuSub,
  SidebarMenuSubButton,
  SidebarMenuSubItem,
  SidebarProvider,
  SidebarTrigger,
  useSidebar,
} from '@/components/ui/sidebar'
import { Separator } from '@/components/ui/separator'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { Badge } from '@/components/ui/badge'
import CommandPalette from '@/components/CommandPalette'
import { Button } from '@/components/ui/button'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuSub,
  DropdownMenuSubContent,
  DropdownMenuSubTrigger,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import {
  LayoutDashboard,
  FileText,
  FolderOpen,
  Clock,
  Bug,
  BarChart3,
  Settings,
  LogOut,
  User,
  ChevronDown,
  Monitor,
  Sun,
  Moon,
  GitBranch,
  Share2,
  Palette,
  ChevronRight,
  TestTube2,
  Sparkles,
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
  BrainCircuitOutlined: Sparkles,
}

// Theme lookup helper — delegates to themes.ts registry
const getTheme = (id: ColorTheme) => getThemeDefinition(id)

export default function MainLayout() {
  const navigate = useNavigate()
  const location = useLocation()
  const { user, projects, currentProjectId, setCurrentProject, projectThemeMap, setProjectTheme, logout } =
    useAuthStore()
  const { mode, colorTheme, setMode, setColorTheme } = useTheme()
  const [menus, setMenus] = useState<MenuItem[]>([])

  useEffect(() => {
    let cancelled = false
    fetchMenus()
      .then((data) => { if (!cancelled) setMenus(data) })
      .catch(() => {})
    return () => { cancelled = true }
  }, [])

  const onSwitchProject = (id: number) => {
    const idNum = Number(id)
    setCurrentProject(idNum)
    // Auto-switch theme if this project has a saved theme
    const saved = projectThemeMap[idNum]
    if (saved) setColorTheme(saved)
    const name = projects.find((p) => p.id === idNum)?.name
    toast.success(`已切换到项目：${name}`)
  }

  const onSetColorAndProject = (theme: ColorTheme) => {
    setColorTheme(theme)
    if (currentProjectId) setProjectTheme(currentProjectId, theme)
  }

  const userInitials = (user?.nickname || user?.username || 'U')[0].toUpperCase()

  // Build menu tree: top-level items + render children as submenus
  const renderMenuItems = (items: typeof menus, depth = 0) => {
    return items.map((m) => {
      const Icon = ICONS[m.icon] ?? LayoutDashboard
      const isActive = location.pathname === m.path ||
        (m.path !== '/' && location.pathname.startsWith(m.path))
      const hasChildren = m.children && m.children.length > 0

      if (hasChildren && depth === 0) {
        // Top-level item with children — render as expandable group
        return (
          <SidebarMenuItem key={m.path || m.code}>
            <SidebarMenuButton
              onClick={() => navigate(m.path)}
              isActive={isActive}
              tooltip={m.name}
              className="peer/menu-parent"
            >
              <Icon />
              <span>{m.name}</span>
              <ChevronRight className="ml-auto size-3.5 transition-transform duration-200 group-data-[state=open]/menu-item:rotate-90" />
            </SidebarMenuButton>
            <SidebarMenuSub>
              {m.children!.map((child) => {
                const ChildIcon = ICONS[child.icon] ?? LayoutDashboard
                const childActive = location.pathname === child.path ||
                  (child.path !== '/' && location.pathname.startsWith(child.path))
                return (
                  <SidebarMenuSubItem key={child.path || child.code}>
                    <SidebarMenuSubButton
                      onClick={() => navigate(child.path)}
                      isActive={childActive}
                    >
                      <ChildIcon className="size-3.5" />
                      <span>{child.name}</span>
                    </SidebarMenuSubButton>
                  </SidebarMenuSubItem>
                )
              })}
            </SidebarMenuSub>
          </SidebarMenuItem>
        )
      }

      // Leaf item or nested child
      return (
        <SidebarMenuItem key={m.path || m.code}>
          <SidebarMenuButton
            onClick={() => navigate(m.path)}
            isActive={isActive}
            tooltip={m.name}
          >
            <Icon />
            <span>{m.name}</span>
          </SidebarMenuButton>
        </SidebarMenuItem>
      )
    })
  }

  // Split menus into primary and secondary groups
  const mainMenus = menus.filter((m) =>
    !['system', 'settings'].includes(m.code?.toLowerCase())
  )
  const systemMenus = menus.filter((m) =>
    ['system', 'settings'].includes(m.code?.toLowerCase())
  )

  return (
    <SidebarProvider defaultOpen>
      {/* ── Skip to content (accessibility) ── */}
      <a href="#main-content" className="sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2 focus:z-50 focus:px-4 focus:py-2 focus:bg-primary focus:text-primary-foreground focus:rounded">
        跳到主内容
      </a>

      {/* ── Sidebar ── */}
      <Sidebar collapsible="icon" aria-label="主导航">
        <SidebarHeader>
          <div className="flex h-14 items-center gap-2.5 px-3 border-b border-sidebar-border">
            {/* Logo icon — always visible, serves as collapsed-state brand */}
            <div className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-sidebar-primary text-sidebar-primary-foreground shadow-sm">
              <TestTube2 className="size-4" />
            </div>
            {/* Text brand — hidden when collapsed */}
            <div className="flex flex-col leading-tight group-data-[collapsible=icon]:hidden">
              <span className="text-sm font-bold sidebar-brand">CamelTv</span>
              <span className="text-[10px] text-sidebar-foreground/50">测试平台</span>
            </div>
          </div>
        </SidebarHeader>

        <SidebarContent>
          <SidebarGroup>
            <SidebarGroupLabel>导航菜单</SidebarGroupLabel>
            <SidebarMenu>
              {renderMenuItems(mainMenus)}
            </SidebarMenu>
          </SidebarGroup>

          {systemMenus.length > 0 && (
            <SidebarGroup>
              <SidebarGroupLabel>系统</SidebarGroupLabel>
              <SidebarMenu>
                {renderMenuItems(systemMenus)}
              </SidebarMenu>
            </SidebarGroup>
          )}
        </SidebarContent>

        {/* ── Sidebar footer: user info ── */}
        <SidebarFooter>
          <div className="flex items-center gap-2.5 px-1 py-1 border-t border-sidebar-border">
            <Avatar className="size-8 shrink-0 ring-2 ring-sidebar-border">
              <AvatarFallback className="text-xs bg-sidebar-accent text-sidebar-accent-foreground font-medium">
                {userInitials}
              </AvatarFallback>
            </Avatar>
            <div className="flex flex-col min-w-0 group-data-[collapsible=icon]:hidden">
              <span className="text-sm font-medium truncate text-sidebar-foreground">
                {user?.nickname || user?.username || '用户'}
              </span>
              <span className="text-[10px] text-sidebar-foreground/50 truncate">
                {user?.email || ''}
              </span>
            </div>
          </div>
        </SidebarFooter>
      </Sidebar>

      {/* ── Main content ── */}
      <SidebarInset className="flex flex-col">
        {/* Header */}
        <header className="flex h-14 shrink-0 items-center justify-between border-b bg-card px-4 glass-card">
          <div className="flex items-center gap-2">
            <SidebarTrigger className="h-8 w-8" />
            <Separator orientation="vertical" className="mx-1 h-6" />
            <span className="text-sm text-muted-foreground">当前项目</span>
            <Select
              value={currentProjectId ? String(currentProjectId) : undefined}
              onValueChange={(v) => onSwitchProject(Number(v))}
            >
              <SelectTrigger className="w-[200px] h-8 text-sm">
                <SelectValue placeholder="选择项目" />
              </SelectTrigger>
              <SelectContent>
                {projects.map((p) => (
                  <SelectItem key={p.id} value={String(p.id)}>
                    {p.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="flex items-center gap-2">
            {/* Theme dropdown — redesigned as card picker */}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="sm" className="gap-1.5">
                  <Palette className="size-4 text-primary" />
                  <span className="hidden sm:inline text-sm font-medium">
                    {getTheme(colorTheme).label}
                  </span>
                  <ChevronDown className="size-3 opacity-50" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-72 p-3">
                {/* Mode toggle */}
                <div className="flex items-center justify-between mb-3">
                  <span className="text-xs font-medium text-muted-foreground">外观模式</span>
                  <div className="flex gap-1 bg-muted rounded-md p-0.5">
                    {(['light', 'dark', 'system'] as const).map((m) => (
                      <button
                        key={m}
                        onClick={() => setMode(m)}
                        className={`px-2.5 py-1 text-xs rounded-sm transition-colors ${
                          mode === m
                            ? 'bg-background text-foreground shadow-sm'
                            : 'text-muted-foreground hover:text-foreground'
                        }`}
                      >
                        {m === 'light' ? <Sun className="size-3.5" /> : m === 'dark' ? <Moon className="size-3.5" /> : <Monitor className="size-3.5" />}
                      </button>
                    ))}
                  </div>
                </div>

                <DropdownMenuSeparator />

                {/* Theme cards grid */}
                <DropdownMenuLabel className="text-xs text-muted-foreground px-0 py-2">
                  主题风格
                </DropdownMenuLabel>
                <div className="grid grid-cols-2 gap-2">
                  {COLOR_THEMES.map((t) => {
                    const isActive = colorTheme === t.id
                    return (
                      <button
                        key={t.id}
                        onClick={() => onSetColorAndProject(t.id)}
                        className={`relative flex flex-col items-start gap-1.5 p-2.5 rounded-lg border-2 transition-all text-left ${
                          isActive
                            ? 'border-primary bg-primary/5 shadow-sm'
                            : 'border-border hover:border-muted-foreground/30 hover:bg-muted/50'
                        }`}
                      >
                        {isActive && (
                          <span className="absolute top-1.5 right-1.5 text-primary text-xs">✓</span>
                        )}
                        {/* Color preview dots */}
                        <div className="flex gap-1">
                          {t.preview.map((color, i) => (
                            <span
                              key={i}
                              className="size-3 rounded-full border border-black/10"
                              style={{ backgroundColor: color }}
                            />
                          ))}
                        </div>
                        <div>
                          <div className="text-xs font-semibold">{t.number} {t.label}</div>
                          <div className="text-[10px] text-muted-foreground leading-tight mt-0.5">
                            {t.description}
                          </div>
                        </div>
                      </button>
                    )
                  })}
                </div>
              </DropdownMenuContent>
            </DropdownMenu>

            {/* User dropdown */}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="sm" className="gap-1.5">
                  <Avatar className="size-6">
                    <AvatarFallback className="text-xs">{userInitials}</AvatarFallback>
                  </Avatar>
                  <span className="hidden sm:inline text-sm">{user?.nickname || user?.username}</span>
                  <ChevronDown className="size-3 opacity-50" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-48">
                <DropdownMenuLabel>
                  <div className="flex flex-col gap-0.5">
                    <span>{user?.nickname || user?.username}</span>
                    {user?.email && (
                      <span className="text-xs font-normal text-muted-foreground">{user.email}</span>
                    )}
                  </div>
                </DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuItem
                  onClick={() => {
                    // P1-1: 先请求后端清除 httpOnly cookie，再清本地状态并跳转。
                    logoutApi().catch(() => {}).finally(() => {
                      logout()
                      navigate('/login', { replace: true })
                    })
                  }}
                >
                  <LogOut className="mr-2 size-4" />
                  <span>退出登录</span>
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </header>

        {/* Page content */}
        <main id="main-content" tabIndex={-1} className="flex-1 overflow-auto p-6 page-enter">
          <Outlet />
        </main>
      </SidebarInset>
      <CommandPalette />
    </SidebarProvider>
  )
}
