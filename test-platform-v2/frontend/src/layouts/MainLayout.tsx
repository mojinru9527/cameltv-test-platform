import { useEffect, useMemo, useState } from 'react'
import { Outlet, useLocation, useNavigate } from 'react-router'
import { toast } from 'sonner'
import { fetchMenus, fetchPublicAccess, logoutApi } from '@/api/auth'
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
  SidebarProvider,
  SidebarTrigger,
} from '@/components/ui/sidebar'
import { Separator } from '@/components/ui/separator'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { Badge, Button } from '@/ui'
import CommandPalette from '@/components/CommandPalette'
import IcpFooter from '@/components/IcpFooter'
import LoginGateDialog from '@/components/auth/LoginGateDialog'
import GuestPlatformHome from './GuestPlatformHome'
import GuestModulePreview from './GuestModulePreview'
import ProjectAccessBoundary from './ProjectAccessBoundary'
import { resolveGuestModule } from './guestModuleCatalog'
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
  LogOut,
  User,
  ChevronDown,
  Monitor,
  Sun,
  Moon,
  Palette,
  TestTube2,
  CheckCircle2,
} from '@/lib/icons'
import { NavigationMenuItems } from './NavigationMenuItems'
import { MoreMenusGroup } from './MoreMenusGroup'
import { splitMenusByFrequency } from './nav-config'

// Theme lookup helper — delegates to themes.ts registry
const getTheme = (id: ColorTheme) => getThemeDefinition(id)

function findMenuLabel(items: MenuItem[], target: string, pathname: string): string {
  const flattened = items.flatMap((item) => [item, ...(item.children || [])])
  return flattened.find((item) => item.path === target)?.name
    || flattened.find((item) => item.path.split('?')[0] === pathname)?.name
    || ''
}

/** 当前用户可见菜单的路径集合（去查询串），供命令面板同步菜单软下线状态。 */
function collectVisibleMenuPaths(items: MenuItem[]): Set<string> {
  const paths = new Set<string>()
  const walk = (list: MenuItem[]) => {
    for (const item of list) {
      if (item.path) paths.add(item.path.split('?')[0])
      if (item.children?.length) walk(item.children)
    }
  }
  walk(items)
  return paths
}

export default function MainLayout() {
  const navigate = useNavigate()
  const location = useLocation()
  const { user, projects, currentProjectId, setCurrentProject, projectThemeMap, setProjectTheme, logout, hasPerm } =
    useAuthStore()
  const { mode, colorTheme, setMode, setColorTheme } = useTheme()
  const [menus, setMenus] = useState<MenuItem[]>([])
  const [menuError, setMenuError] = useState(false)
  const [menuRequest, setMenuRequest] = useState(0)
  const [registrationEnabled, setRegistrationEnabled] = useState(true)
  const [loginTarget, setLoginTarget] = useState<{ path: string; label: string } | null>(null)
  const isAuthenticated = Boolean(user)
  const activeTheme = getTheme(colorTheme)
  const isObsidian = colorTheme === 'obsidian-flow'
  const modeOptions: ThemeMode[] = activeTheme.supportedModes.length === 1
    ? [...activeTheme.supportedModes]
    : [...activeTheme.supportedModes, 'system']

  useAbortableEffect((signal) => {
    setMenuError(false)
    const request = isAuthenticated ? fetchMenus(signal) : fetchPublicAccess(signal)
    request
      .then((data) => {
        if (!signal.aborted) {
          if (Array.isArray(data)) {
            setMenus(data)
          } else {
            setMenus(data.modules)
            setRegistrationEnabled(data.registration_enabled)
          }
          setMenuError(false)
        }
      })
      .catch(() => {
        if (!signal.aborted) {
          setMenuError(true)
        }
      })
  }, [isAuthenticated, menuRequest])

  useEffect(() => {
    document.getElementById('main-content')?.focus()
  }, [location.pathname])

  const visibleMenuPaths = useMemo(() => collectVisibleMenuPaths(menus), [menus])

  const navigateMenu = (path: string) => {
    navigate(path || '/')
  }

  const requireLogin = (path: string, label = '该模块') => {
    setLoginTarget({ path: path || '/', label })
  }

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

  // (c165-3) 导航按使用频率分层：9 个高频平铺，其余一级菜单收进「更多功能」折叠组
  // （fail-safe：未在 PRIMARY_MENU_CODES 中的 code 一律落入 more）。
  // 原 knowledge/system 特例分组随之移除（system 过滤以 'system' 对比 'menu:system'
  // 形式的 code，从未命中，属死逻辑）。
  const { primary: primaryMenus, more: moreMenus } = useMemo(
    () => splitMenusByFrequency(menus),
    [menus],
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
              <span className="text-sm font-bold sidebar-brand">测试平台</span>
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
          {/* ── 高频导航（c165-3 频率分层）── */}
          <SidebarGroup>
            <SidebarGroupLabel>导航菜单</SidebarGroupLabel>
            <SidebarMenu>
              <NavigationMenuItems
                items={primaryMenus}
                pathname={location.pathname}
                onNavigate={navigateMenu}
              />
            </SidebarMenu>
          </SidebarGroup>

          {/* ── 低频入口：「更多功能」折叠组（默认收起）── */}
          <MoreMenusGroup
            items={moreMenus}
            pathname={location.pathname}
            onNavigate={navigateMenu}
          />
        </SidebarContent>

        {/* ── Sidebar footer: user info ── */}
        <SidebarFooter>
          {isAuthenticated ? (
            <div className="flex items-center gap-2.5 border-t border-sidebar-border px-1 py-1">
              <Avatar className="size-8 shrink-0 ring-2 ring-sidebar-border">
                <AvatarFallback className="bg-sidebar-accent text-xs font-medium text-sidebar-accent-foreground">
                  {userInitials}
                </AvatarFallback>
              </Avatar>
              <div className="flex min-w-0 flex-col group-data-[collapsible=icon]:hidden">
                <span className="truncate text-sm font-medium text-sidebar-foreground">
                  {user?.nickname || user?.username || '用户'}
                </span>
                <span className="truncate text-xs text-sidebar-foreground">
                  {user?.email || ''}
                </span>
              </div>
            </div>
          ) : (
            <Button
              type="button"
              variant="secondary"
              className="w-full group-data-[collapsible=icon]:px-0"
              onClick={() => requireLogin('/workbench', '工作台')}
            >
              <User className="size-4" aria-hidden="true" />
              <span className="group-data-[collapsible=icon]:hidden">登录平台</span>
            </Button>
          )}
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
            {isAuthenticated ? (
              <>
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
              </>
            ) : (
              <Badge variant="secondary">公开浏览</Badge>
            )}
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
            {isAuthenticated ? (
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
                    <span className="hidden text-sm sm:inline">{user?.nickname || user?.username}</span>
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
                        navigate('/', { replace: true })
                      })
                    }}
                  >
                    <LogOut className="mr-2 size-4" />
                    <span>退出登录</span>
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            ) : (
              <Button
                type="button"
                size="sm"
                className="!min-h-11"
                onClick={() => requireLogin('/workbench', '工作台')}
              >
                登录
              </Button>
            )}
          </div>
        </header>

        {/* Page content */}
        <main id="main-content" tabIndex={-1} className="min-w-0 flex-1 overflow-auto p-4 page-enter sm:p-6">
          {isAuthenticated ? (
            <ProjectAccessBoundary
              projectId={currentProjectId}
              pathname={location.pathname}
              canCreateProject={hasPerm('project:self_create') || hasPerm('project:create') || hasPerm('*')}
              onOpenProjects={() => navigate('/my-projects')}
            >
              <Outlet />
            </ProjectAccessBoundary>
          ) : location.pathname === '/' ? (
            <GuestPlatformHome
              modules={menus}
              registrationEnabled={registrationEnabled}
              onNavigate={navigateMenu}
              onRequireLogin={requireLogin}
            />
          ) : (
            <GuestModulePreview
              module={resolveGuestModule(
                location.pathname,
                location.search,
                findMenuLabel(menus, `${location.pathname}${location.search}`, location.pathname),
              )}
              path={`${location.pathname}${location.search}`}
              registrationEnabled={registrationEnabled}
              onRequireLogin={requireLogin}
            />
          )}
        </main>
        <IcpFooter />
      </SidebarInset>
      {isAuthenticated && <CommandPalette visibleMenuPaths={visibleMenuPaths} />}
      <LoginGateDialog
        open={!isAuthenticated && Boolean(loginTarget)}
        destinationLabel={loginTarget?.label || '该模块'}
        registrationEnabled={registrationEnabled}
        onOpenChange={(open) => {
          if (!open) setLoginTarget(null)
        }}
        onLoginSuccess={() => {
          const destination = loginTarget?.path || '/workbench'
          setLoginTarget(null)
          navigate(destination)
        }}
      />
    </SidebarProvider>
  )
}
