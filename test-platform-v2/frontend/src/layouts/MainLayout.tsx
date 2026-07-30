import { useEffect, useState } from 'react'
import { Outlet, useLocation, useNavigate } from 'react-router'
import { toast } from 'sonner'
import { fetchMenus, logoutApi } from '@/api/auth'
import { useAuthStore } from '@/stores/auth'
import type { ColorTheme } from '@/stores/auth'
import { useTheme, type ThemeMode } from '@/components/theme-provider'
import useAbortableEffect from '@/hooks/useAbortableEffect'
import { COLOR_THEMES, getThemeDefinition, normalizeColorTheme } from '@/lib/themes'
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
import { Badge } from '@/ui'
import CommandPalette from '@/components/CommandPalette'
import { Button } from '@/ui'
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
  TestTube2,
  Sparkles,
  Cpu,
  CheckCircle2,
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
  SparklesOutlined: Sparkles,
  GitBranchOutlined: GitBranch,
  FolderOpenOutlined: FolderOpen,
  CpuOutlined: Cpu,
}

// Theme lookup helper — delegates to themes.ts registry
const getTheme = (id: ColorTheme) => getThemeDefinition(id)

function NavigationMenuItems({
  items,
  pathname,
  onNavigate,
}: {
  items: MenuItem[]
  pathname: string
  onNavigate: (path: string) => void
}) {
  const { isMobile, setOpenMobile } = useSidebar()

  const goTo = (path: string) => {
    onNavigate(path)
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
            onClick={() => goTo(m.path)}
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
                    onClick={() => goTo(child.path)}
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
          onClick={() => goTo(m.path)}
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

export default function MainLayout() {
  const navigate = useNavigate()
  const location = useLocation()
  const { user, projects, currentProjectId, setCurrentProject, projectThemeMap, setProjectTheme, logout } =
    useAuthStore()
  const { mode, colorTheme, setMode, setColorTheme } = useTheme()
  const [menus, setMenus] = useState<MenuItem[]>([])
  const [menuError, setMenuError] = useState(false)
  const [menuRequest, setMenuRequest] = useState(0)
  const activeTheme = getTheme(colorTheme)
  const isObsidian = colorTheme === 'obsidian-flow'
  const modeOptions: ThemeMode[] = activeTheme.supportedModes.length === 1
    ? [...activeTheme.supportedModes]
    : [...activeTheme.supportedModes, 'system']

  useAbortableEffect((signal) => {
    setMenuError(false)
    fetchMenus(signal)
      .then((data) => {
        if (!signal.aborted) {
          setMenus(data)
          setMenuError(false)
        }
      })
      .catch(() => {
        if (!signal.aborted) {
          setMenuError(true)
        }
      })
  }, [menuRequest])

  useEffect(() => {
    document.getElementById('main-content')?.focus()
  }, [location.pathname])

  const applyColorTheme = (theme: ColorTheme) => {
    const definition = getTheme(theme)
    if (definition.supportedModes.length === 1) {
      setMode(definition.preferredMode)
    }
    setColorTheme(theme)
  }

  const onSwitchProject = (id: number) => {
    const idNum = Number(id)
    setCurrentProject(idNum)
    // Auto-switch theme if this project has a saved theme
    const saved = projectThemeMap[idNum]
    if (saved) applyColorTheme(normalizeColorTheme(saved))
    const name = projects.find((p) => p.id === idNum)?.name
    toast.success(`已切换到项目：${name}`)
  }

  const onSetColorAndProject = (theme: ColorTheme) => {
    applyColorTheme(theme)
    if (currentProjectId) setProjectTheme(currentProjectId, theme)
  }

  const userInitials = (user?.nickname || user?.username || 'U')[0].toUpperCase()

  // 未完成模块：隐藏在导航菜单，路由仍可访问
  const HIDDEN_MENU_CODES = new Set([
    'menu:versionmission',
    'menu:defect',
    'menu:dataset',
    'menu:integration',
  ])

  // Split menus into three groups: knowledge, primary nav, system
  const knowledgeMenus = menus.filter((m) =>
    m.code?.startsWith("menu:knowledge") && !HIDDEN_MENU_CODES.has(m.code ?? '')
  )
  const systemMenus = menus.filter((m) =>
    ['system', 'settings'].includes(m.code?.toLowerCase()) && !HIDDEN_MENU_CODES.has(m.code ?? '')
  )
  const mainMenus = menus.filter((m) =>
    !['system', 'settings'].includes(m.code?.toLowerCase()) &&
    !m.code?.startsWith("menu:knowledge") &&
    !HIDDEN_MENU_CODES.has(m.code ?? '')
  )

  return (
    <SidebarProvider defaultOpen>
      {/* ── Skip to content (accessibility) ── */}
      <a href="#main-content" className="sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2 focus:z-50 focus:px-4 focus:py-2 focus:bg-primary focus:text-primary-foreground focus:rounded">
        跳到主内容
      </a>

      {/* ── Sidebar ── */}
      <Sidebar collapsible="icon" aria-label="主导航" className={isObsidian ? 'ui-glass' : ''}>
        <SidebarHeader>
          <div className="flex h-14 items-center gap-2.5 px-3 border-b border-sidebar-border">
            {/* Logo icon — always visible, serves as collapsed-state brand */}
            <div className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-sidebar-primary text-sidebar-primary-foreground shadow-sm">
              <TestTube2 className="size-4" />
            </div>
            {/* Text brand — hidden when collapsed */}
            <div className="flex flex-col leading-tight group-data-[collapsible=icon]:hidden">
              <span className="text-sm font-bold sidebar-brand">CamelTv</span>
              <span className="text-xs text-sidebar-foreground">测试平台</span>
            </div>
          </div>
        </SidebarHeader>

        <SidebarContent>
          {menuError && (
            <div
              role="alert"
              className="mx-2 rounded-lg border border-[var(--color-status-danger-border)] bg-[var(--color-status-danger-bg)] p-3 text-sm"
            >
              <p className="font-medium text-[var(--color-status-danger)]">导航菜单加载失败</p>
              <p className="mt-1 text-xs text-muted-foreground">请检查网络后重新加载。</p>
              <Button
                size="sm"
                variant="secondary"
                className="mt-3 w-full"
                onClick={() => setMenuRequest((value) => value + 1)}
              >
                重新加载导航菜单
              </Button>
            </div>
          )}
          {/* ── 知识 (Knowledge) ── */}
          {knowledgeMenus.length > 0 && (
            <SidebarGroup>
              <SidebarGroupLabel>知识</SidebarGroupLabel>
              <SidebarMenu>
                <NavigationMenuItems
                  items={knowledgeMenus}
                  pathname={location.pathname}
                  onNavigate={navigate}
                />
              </SidebarMenu>
            </SidebarGroup>
          )}

          <SidebarGroup>
            <SidebarGroupLabel>导航菜单</SidebarGroupLabel>
            <SidebarMenu>
              <NavigationMenuItems
                items={mainMenus}
                pathname={location.pathname}
                onNavigate={navigate}
              />
            </SidebarMenu>
          </SidebarGroup>

          {systemMenus.length > 0 && (
            <SidebarGroup>
              <SidebarGroupLabel>系统</SidebarGroupLabel>
              <SidebarMenu>
                <NavigationMenuItems
                  items={systemMenus}
                  pathname={location.pathname}
                  onNavigate={navigate}
                />
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
              <span className="text-xs text-sidebar-foreground truncate">
                {user?.email || ''}
              </span>
            </div>
          </div>
        </SidebarFooter>
      </Sidebar>

      {/* ── Main content ── */}
      <SidebarInset className={`flex flex-col ${isObsidian ? '' : colorTheme === 'liquid-glass' ? 'lg-morph-bg' : ''}`}>
        {/* Header */}
        <header className={`flex h-14 shrink-0 items-center justify-between gap-1 border-b px-2 sm:px-4 ${
          isObsidian
            ? 'ui-glass'
            : 'bg-card glass-card'
        }`}>
          <div className="flex min-w-0 items-center gap-1 sm:gap-2">
            <SidebarTrigger className="!size-11" />
            <Separator orientation="vertical" className="mx-1 hidden h-6 sm:block" />
            <span className="hidden text-sm text-muted-foreground lg:inline">当前项目</span>
            <Select
              value={currentProjectId ? String(currentProjectId) : undefined}
              onValueChange={(v) => onSwitchProject(Number(v))}
            >
              <SelectTrigger
                className="!h-11 w-[150px] min-w-0 text-sm sm:w-[200px]"
                aria-label="当前项目"
              >
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

          <div className="flex shrink-0 items-center gap-0 sm:gap-2">
            {/* Theme dropdown — redesigned as card picker */}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button
                  variant="ghost"
                  size="sm"
                  className="!min-h-11 !min-w-11 gap-1.5"
                  aria-label={`切换主题，当前${activeTheme.label}`}
                >
                  <Palette className="size-4 text-primary" />
                  <span className="hidden sm:inline text-sm font-medium">
                    {activeTheme.label}
                  </span>
                  <ChevronDown className="hidden size-3 opacity-50 sm:block" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-72 p-3">
                {/* Mode toggle */}
                <div className="flex items-center justify-between mb-3">
                  <span className="text-xs font-medium text-muted-foreground">外观模式</span>
                  <div className="flex gap-1 bg-muted rounded-md p-0.5">
                    {modeOptions.map((m) => (
                      <button
                        key={m}
                        onClick={() => setMode(m)}
                        aria-label={m === 'light' ? '浅色模式' : m === 'dark' ? '深色模式' : '跟随系统'}
                        className={`min-h-11 min-w-11 px-2.5 py-1 text-xs rounded-sm transition-colors ${
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
                {isObsidian && (
                  <p className="-mt-1 mb-3 text-xs text-muted-foreground">
                    黑曜流界为深色专属
                  </p>
                )}

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
                        type="button"
                        onClick={() => onSetColorAndProject(t.id)}
                        className={`relative flex flex-col items-start gap-1.5 p-2.5 rounded-lg border-2 transition-colors duration-200 text-left ${
                          isActive
                            ? 'border-primary bg-primary/5 shadow-sm'
                            : 'border-border hover:border-muted-foreground/30 hover:bg-muted/50'
                        }`}
                      >
                        {isActive && (
                          <CheckCircle2 className="absolute right-1.5 top-1.5 size-3.5 text-primary" aria-label="当前主题" />
                        )}
                        {/* Color preview dots */}
                        <div className="flex gap-1">
                          {t.preview.map((color, i) => (
                            <span
                              key={i}
                              className="size-3 rounded-full border border-border"
                              style={{ backgroundColor: color }}
                            />
                          ))}
                        </div>
                        <div>
                          <div className="text-xs font-semibold">{t.number} {t.label}</div>
                          <div className="text-xs text-muted-foreground leading-tight mt-0.5">
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
                <Button
                  variant="ghost"
                  size="sm"
                  className="!min-h-11 !min-w-11 gap-1.5"
                  aria-label={`用户菜单：${user?.nickname || user?.username || '用户'}`}
                >
                  <Avatar className="size-6">
                    <AvatarFallback className="text-xs">{userInitials}</AvatarFallback>
                  </Avatar>
                  <span className="hidden sm:inline text-sm">{user?.nickname || user?.username}</span>
                  <ChevronDown className="hidden size-3 opacity-50 sm:block" />
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
        <main id="main-content" tabIndex={-1} className="min-w-0 flex-1 overflow-auto p-4 page-enter sm:p-6">
          <Outlet />
        </main>
      </SidebarInset>
      <CommandPalette />
    </SidebarProvider>
  )
}
