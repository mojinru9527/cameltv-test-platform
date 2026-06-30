import { useEffect, useState } from 'react'
import { Outlet, useLocation, useNavigate } from 'react-router-dom'
import { toast } from 'sonner'
import { fetchMenus } from '@/api/auth'
import { useAuthStore } from '@/stores/auth'
import type { ColorTheme } from '@/stores/auth'
import { useTheme } from '@/components/theme-provider'
import type { MenuItem } from '@/types'
import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarInset,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarProvider,
  SidebarTrigger,
} from '@/components/ui/sidebar'
import { Separator } from '@/components/ui/separator'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
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
}

const THEME_LABELS: Record<ColorTheme, string> = {
  blue: '极客蓝',
  green: '翡翠绿',
  purple: '星空紫',
  orange: '活力橙',
  rose: '玫瑰红',
  cyan: '青碧色',
  amber: '琥珀金',
  indigo: '幽兰紫',
}

const THEME_COLORS: Record<ColorTheme, string> = {
  blue: 'bg-blue-600',
  green: 'bg-emerald-600',
  purple: 'bg-purple-600',
  orange: 'bg-orange-500',
  rose: 'bg-rose-600',
  cyan: 'bg-cyan-600',
  amber: 'bg-amber-500',
  indigo: 'bg-indigo-600',
}

export default function MainLayout() {
  const navigate = useNavigate()
  const location = useLocation()
  const { user, projects, currentProjectId, setCurrentProject, projectThemeMap, setProjectTheme, logout } =
    useAuthStore()
  const { mode, colorTheme, setMode, setColorTheme } = useTheme()
  const [menus, setMenus] = useState<MenuItem[]>([])

  useEffect(() => {
    fetchMenus()
      .then(setMenus)
      .catch(() => {})
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

  return (
    <SidebarProvider defaultOpen>
      {/* ── Sidebar ── */}
      <Sidebar collapsible="icon">
        <SidebarHeader className="flex h-14 items-center justify-center border-b border-sidebar-border">
          <span className="text-base font-semibold text-sidebar-foreground">
            CamelTv 测试平台
          </span>
        </SidebarHeader>

        <SidebarContent>
          <SidebarGroup>
            <SidebarGroupLabel>导航菜单</SidebarGroupLabel>
            <SidebarMenu>
              {menus.map((m) => {
                const Icon = ICONS[m.icon] ?? LayoutDashboard
                const isActive = location.pathname === m.path ||
                  (m.path !== '/' && location.pathname.startsWith(m.path))
                return (
                  <SidebarMenuItem key={m.path}>
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
              })}
            </SidebarMenu>
          </SidebarGroup>
        </SidebarContent>
      </Sidebar>

      {/* ── Main content ── */}
      <SidebarInset className="flex flex-col">
        {/* Header */}
        <header className="flex h-14 shrink-0 items-center justify-between border-b bg-card px-4">
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
            {/* Theme dropdown */}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="sm">
                  <Palette className="size-4" />
                  <span className="ml-1 hidden sm:inline">{THEME_LABELS[colorTheme]}</span>
                  <ChevronDown className="size-3 opacity-50" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-48">
                <DropdownMenuLabel>外观设置</DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuGroup>
                  <DropdownMenuItem onClick={() => setMode('light')}>
                    <Sun className="mr-2 size-4" />
                    <span>浅色</span>
                    {mode === 'light' && <span className="ml-auto text-xs text-muted-foreground">✓</span>}
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => setMode('dark')}>
                    <Moon className="mr-2 size-4" />
                    <span>暗色</span>
                    {mode === 'dark' && <span className="ml-auto text-xs text-muted-foreground">✓</span>}
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => setMode('system')}>
                    <Monitor className="mr-2 size-4" />
                    <span>跟随系统</span>
                    {mode === 'system' && <span className="ml-auto text-xs text-muted-foreground">✓</span>}
                  </DropdownMenuItem>
                </DropdownMenuGroup>
                <DropdownMenuSeparator />
                <DropdownMenuLabel>主题色彩</DropdownMenuLabel>
                <DropdownMenuGroup>
                  {(Object.keys(THEME_COLORS) as ColorTheme[]).map((t) => (
                    <DropdownMenuItem key={t} onClick={() => onSetColorAndProject(t)}>
                      <span className={`mr-2 size-3 rounded-full ${THEME_COLORS[t]}`} />
                      <span>{THEME_LABELS[t]}</span>
                      {colorTheme === t && <span className="ml-auto text-xs text-muted-foreground">✓</span>}
                    </DropdownMenuItem>
                  ))}
                </DropdownMenuGroup>
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
                    logout()
                    navigate('/login', { replace: true })
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
        <main className="flex-1 overflow-auto p-6">
          <Outlet />
        </main>
      </SidebarInset>
    </SidebarProvider>
  )
}
