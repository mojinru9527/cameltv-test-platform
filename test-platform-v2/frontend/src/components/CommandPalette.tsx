import { useEffect, useState, useCallback, useMemo } from 'react'
import { useNavigate } from 'react-router'
import {
  CommandDialog,
  CommandInput,
  CommandList,
  CommandEmpty,
  CommandGroup,
  CommandItem,
  CommandShortcut,
} from '@/components/ui/command'
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
  Bell,
  Globe,
  Database,
  Link2,
  Terminal,
  type LucideIcon,
} from '@/lib/icons'
import { useAuthStore } from '@/stores/auth'

export interface CommandRoute {
  label: string
  path: string
  icon: LucideIcon
  group: string
  /** 需要该权限才可见（缺省 = 登录即可见） */
  permission?: string
  /** 入口由菜单种子背书：菜单被 DISABLED_MENUS 软下线时同步从命令面板隐藏 */
  menuBacked?: boolean
}

// Route registry — all searchable pages（与 router/seed 菜单对账）
export const ALL_COMMAND_ROUTES: CommandRoute[] = [
  { label: '工作台', path: '/workbench', icon: LayoutDashboard, group: '页面' },
  { label: '用例服务', path: '/testcase', icon: FileText, group: '页面' },
  { label: '测试计划', path: '/testplan', icon: FolderOpen, group: '页面' },
  { label: '需求文档', path: '/requirement', icon: GitBranch, group: '页面' },
  { label: '报告中心', path: '/report', icon: BarChart3, group: '页面' },
  { label: '定时任务', path: '/schedule', icon: Clock, group: '页面' },
  { label: '缺陷管理', path: '/defect', icon: Bug, group: '页面' },
  { label: '质量追溯', path: '/trace', icon: Share2, group: '页面' },
  // (P2a) 思维导图并入用例服务「脑图视图」Tab，入口指向带参路径
  { label: '思维导图', path: '/testcase?tab=mindmap', icon: Share2, group: '页面' },
  { label: '版本发布包', path: '/release-bundles', icon: GitBranch, group: '页面' },
  { label: '知识中心', path: '/knowledge', icon: Sparkles, group: '页面' },
  { label: '测试数据集', path: '/dataset', icon: Database, group: '页面' },
  // (P2b) Playground 并入用例服务 Tab，入口指向带参路径
  { label: 'Playground', path: '/testcase?tab=playground', icon: Terminal, group: '页面' },
  { label: '集成配置', path: '/integration', icon: Link2, group: '页面', menuBacked: true },
  { label: '目标环境', path: '/environment', icon: Globe, group: '页面' },
  { label: '通知配置', path: '/notify', icon: Bell, group: '页面', menuBacked: true },
  { label: '我的项目', path: '/my-projects', icon: Settings, group: '页面' },
  { label: '系统管理', path: '/system', icon: Settings, group: '页面' },
  { label: '接口测试', path: '/apitest', icon: FileText, group: '页面' },
  { label: 'UI 自动化', path: '/uitest', icon: FileText, group: '页面' },
  // (P1b) Agent 工作台已收敛进 DSH 任务，路由重定向 /dsh-tasks，入口不再单列
  { label: '运维发布记录', path: '/operations-release', icon: FileText, group: '页面', permission: 'release:view' },
]

export function filterCommandRoutes(
  routes: CommandRoute[],
  hasPerm: (code: string) => boolean,
  visibleMenuPaths?: ReadonlySet<string>,
): CommandRoute[] {
  return routes.filter((route) => {
    if (route.permission && !hasPerm(route.permission)) return false
    // menuBacked 条目跟随菜单可见性（DISABLED_MENUS 软下线即隐藏）；
    // 未传菜单路径集合时保持旧行为（仅按权限过滤），兼容既有调用方。
    if (route.menuBacked && visibleMenuPaths && !visibleMenuPaths.has(route.path)) return false
    return true
  })
}

export default function CommandPalette({ visibleMenuPaths }: { visibleMenuPaths?: ReadonlySet<string> }) {
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const hasPerm = useAuthStore((state) => state.hasPerm)

  // Ctrl+K / Cmd+K to toggle
  const onKeyDown = useCallback((e: KeyboardEvent) => {
    if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
      e.preventDefault()
      setOpen((prev) => !prev)
    }
    // Escape to close
    if (e.key === 'Escape' && open) {
      setOpen(false)
    }
  }, [open])

  useEffect(() => {
    document.addEventListener('keydown', onKeyDown)
    return () => document.removeEventListener('keydown', onKeyDown)
  }, [onKeyDown])

  const filtered = useMemo(() => {
    const visible = filterCommandRoutes(ALL_COMMAND_ROUTES, hasPerm, visibleMenuPaths)
    if (!query.trim()) return visible
    const q = query.toLowerCase()
    return visible.filter(
      (r) =>
        r.label.toLowerCase().includes(q) ||
        r.path.toLowerCase().includes(q) ||
        r.group.toLowerCase().includes(q),
    )
  }, [query, hasPerm, visibleMenuPaths])

  const groups = useMemo(() => {
    const map = new Map<string, CommandRoute[]>()
    filtered.forEach((r) => {
      const list = map.get(r.group) || []
      list.push(r)
      map.set(r.group, list)
    })
    return Array.from(map.entries())
  }, [filtered])

  return (
    <CommandDialog open={open} onOpenChange={setOpen}>
      <CommandInput
        placeholder="搜索页面..."
        value={query}
        onValueChange={setQuery}
      />
      <CommandList>
        <CommandEmpty>未找到匹配的页面</CommandEmpty>
        {groups.map(([group, routes]) => (
          <CommandGroup key={group} heading={group}>
            {routes.map((r) => (
              <CommandItem
                key={r.path}
                value={r.label}
                onSelect={() => {
                  navigate(r.path)
                  setOpen(false)
                }}
              >
                <r.icon className="size-4 text-muted-foreground" />
                <span>{r.label}</span>
                <CommandShortcut>{r.path}</CommandShortcut>
              </CommandItem>
            ))}
          </CommandGroup>
        ))}
      </CommandList>
    </CommandDialog>
  )
}
