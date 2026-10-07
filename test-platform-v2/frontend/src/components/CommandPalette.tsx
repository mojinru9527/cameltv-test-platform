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
} from '@/ui'
import {
  LayoutDashboard,
  FileText,
  Clock,
  Bug,
  Settings,
  GitBranch,
  Share2,
  Sparkles,
  Globe,
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
  /**
   * 搜索别名（P2-10）。命令面板此前只按 label/path/group 匹配，
   * 搜「Mission」「AI」「场景」「契约」全部 0 结果，V4.0 新功能无法被检索到。
   */
  keywords?: string[]
}

// Route registry — all searchable pages（与 router/seed 菜单对账）
// 平台简化批次：AITDE/DSH/报告/数据集/集成/通知等已删除，命令面板同步收敛。
export const ALL_COMMAND_ROUTES: CommandRoute[] = [
  { label: '工作台', menuBacked: true, path: '/workbench', icon: LayoutDashboard, group: '页面', keywords: ['dashboard', '首页', '看板'] },
  { label: '用例服务', menuBacked: true, path: '/testcase', icon: FileText, group: '页面', keywords: ['case', '用例'] },
  { label: '需求文档', menuBacked: true, path: '/requirement', icon: GitBranch, group: '页面', keywords: ['prd', '需求', 'ai 拆分', '生成用例'] },
  { label: '定时任务', menuBacked: true, path: '/schedule', icon: Clock, group: '页面', keywords: ['cron', '定时'] },
  { label: '缺陷管理', menuBacked: true, path: '/defect', icon: Bug, group: '页面', keywords: ['bug', '缺陷'] },
  // (P2a) 思维导图并入用例服务「脑图视图」Tab，入口指向带参路径
  { label: '思维导图', path: '/testcase?tab=mindmap', icon: Share2, group: '页面', keywords: ['mindmap', '脑图'] },
  { label: '版本发布包', menuBacked: true, path: '/release-bundles', icon: GitBranch, group: '页面', keywords: ['release', '发布'] },
  { label: '版本验收任务', menuBacked: true, path: '/version-tasks', icon: GitBranch, group: '页面', keywords: ['version', '版本', '验收'] },
  { label: '知识中心', menuBacked: true, path: '/knowledge', icon: Sparkles, group: '页面', keywords: ['knowledge', '知识', 'wiki', 'rag'] },
  { label: '目标环境', menuBacked: true, path: '/environment', icon: Globe, group: '页面', keywords: ['env', '环境'] },
  { label: '我的项目', menuBacked: true, path: '/my-projects', icon: Settings, group: '页面', keywords: ['project', '项目'] },
  { label: '系统管理', menuBacked: true, path: '/system', icon: Settings, group: '页面', keywords: ['system', '用户', '角色', '权限'] },
  { label: '接口测试', menuBacked: true, path: '/apitest', icon: FileText, group: '页面', keywords: ['api', '接口'] },
  { label: 'UI 自动化', menuBacked: true, path: '/uitest', icon: FileText, group: '页面', keywords: ['ui', 'playwright', '自动化'] },
  { label: 'AI 配置', menuBacked: true, path: '/ai-config', icon: Sparkles, group: '页面', keywords: ['ai', '模型', 'key', '大模型', 'llm'] },
  { label: '蓝湖证据包', menuBacked: true, path: '/lanhu-evidence', icon: Terminal, group: '页面', keywords: ['lanhu', '蓝湖', '证据'] },
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

/** 命令面板匹配：label / path / group / keywords 任一命中（P2-10）。 */
export function matchesQuery(route: CommandRoute, query: string): boolean {
  const q = query.trim().toLowerCase()
  if (!q) return true
  return (
    route.label.toLowerCase().includes(q) ||
    route.path.toLowerCase().includes(q) ||
    route.group.toLowerCase().includes(q) ||
    (route.keywords ?? []).some((k) => k.toLowerCase().includes(q))
  )
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
    return visible.filter((r) => matchesQuery(r, query))
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
    <CommandDialog open={open} onOpenChange={setOpen} shouldFilter={false}>
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
