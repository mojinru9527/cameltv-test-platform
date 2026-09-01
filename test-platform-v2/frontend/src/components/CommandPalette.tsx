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
import { useAitdeV3Enabled } from '@/config/aitde'

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
  /** 仅在后端开启 AITDE 时展示（V4.0 主链入口）。 */
  requiresAitde?: boolean
}

// Route registry — all searchable pages（与 router/seed 菜单对账）
export const ALL_COMMAND_ROUTES: CommandRoute[] = [
  { label: '工作台', path: '/workbench', icon: LayoutDashboard, group: '页面', keywords: ['dashboard', '首页', '看板'] },
  // ── V4.0 AITDE 主链（P2-10：补齐命令面板收录 + 别名）──
  {
    label: '智能测试任务',
    path: '/missions',
    icon: Sparkles,
    group: 'AITDE',
    requiresAitde: true,
    keywords: ['mission', '任务', 'aitde', '契约', 'contract', '场景', 'scenario', '主链', 'v4'],
  },
  {
    label: 'AI 建议收件箱',
    path: '/ai-suggestions',
    icon: Sparkles,
    group: 'AITDE',
    requiresAitde: true,
    keywords: ['ai', 'suggestion', '建议', '收件箱'],
  },
  {
    label: '执行中心',
    path: '/executions',
    icon: Terminal,
    group: 'AITDE',
    requiresAitde: true,
    keywords: ['run', 'execution', '执行', '回放', 'replay'],
  },
  {
    label: '愈合评审',
    path: '/healing',
    icon: Sparkles,
    group: 'AITDE',
    requiresAitde: true,
    keywords: ['healing', '自愈', '愈合', 'ai'],
  },
  {
    label: 'Flaky 分析',
    path: '/flaky',
    icon: BarChart3,
    group: 'AITDE',
    requiresAitde: true,
    keywords: ['flaky', '不稳定', '抖动'],
  },
  {
    label: '数据源',
    path: '/data-sources',
    icon: Database,
    group: 'AITDE',
    requiresAitde: true,
    keywords: ['data source', '数据源', 'fixture'],
  },
  {
    label: 'Fixture',
    path: '/fixtures',
    icon: Database,
    group: 'AITDE',
    requiresAitde: true,
    keywords: ['fixture', '夹具', '测试数据'],
  },
  {
    label: 'Durable Runtime',
    path: '/admin/workers',
    icon: Terminal,
    group: 'AITDE',
    requiresAitde: true,
    keywords: ['worker', 'runtime', 'temporal', '运行时'],
  },
  { label: '用例服务', path: '/testcase', icon: FileText, group: '页面', keywords: ['case', '用例'] },
  { label: '测试计划', path: '/testplan', icon: FolderOpen, group: '页面', keywords: ['plan', '计划'] },
  { label: '需求文档', path: '/requirement', icon: GitBranch, group: '页面', keywords: ['prd', '需求', 'ai 拆分', '生成用例'] },
  { label: '报告中心', path: '/report', icon: BarChart3, group: '页面', keywords: ['report', '报告'] },
  { label: '定时任务', path: '/schedule', icon: Clock, group: '页面', keywords: ['cron', '定时'] },
  { label: '缺陷管理', path: '/defect', icon: Bug, group: '页面', keywords: ['bug', '缺陷'] },
  // (P2c) 质量追溯并入报告中心 Tab，入口指向带参路径
  { label: '质量追溯', path: '/report?tab=trace', icon: Share2, group: '页面', keywords: ['trace', '追溯'] },
  // (P2a) 思维导图并入用例服务「脑图视图」Tab，入口指向带参路径
  { label: '思维导图', path: '/testcase?tab=mindmap', icon: Share2, group: '页面', keywords: ['mindmap', '脑图'] },
  { label: '版本发布包', path: '/release-bundles', icon: GitBranch, group: '页面', keywords: ['release', '发布'] },
  { label: '知识中心', path: '/knowledge', icon: Sparkles, group: '页面', keywords: ['knowledge', '知识', 'wiki', 'rag'] },
  { label: '测试数据集', path: '/dataset', icon: Database, group: '页面', keywords: ['dataset', '数据集'] },
  // (P2b) Playground 并入用例服务 Tab，入口指向带参路径
  { label: 'Playground', path: '/testcase?tab=playground', icon: Terminal, group: '页面' },
  { label: '集成配置', path: '/integration', icon: Link2, group: '页面', menuBacked: true },
  { label: '目标环境', path: '/environment', icon: Globe, group: '页面', keywords: ['env', '环境'] },
  { label: '通知配置', path: '/notify', icon: Bell, group: '页面', menuBacked: true },
  { label: '我的项目', path: '/my-projects', icon: Settings, group: '页面', keywords: ['project', '项目'] },
  { label: '系统管理', path: '/system', icon: Settings, group: '页面', keywords: ['system', '用户', '角色', '权限'] },
  { label: '接口测试', path: '/apitest', icon: FileText, group: '页面', keywords: ['api', '接口'] },
  { label: 'UI 自动化', path: '/uitest', icon: FileText, group: '页面', keywords: ['ui', 'playwright', '自动化'] },
  { label: 'DSH 任务', path: '/dsh-tasks', icon: Terminal, group: '页面', keywords: ['dsh', 'agent', 'ai', '智能体', '生成用例'] },
  { label: 'AI 配置', path: '/ai-config', icon: Sparkles, group: '页面', keywords: ['ai', '模型', 'key', '大模型', 'llm'] },
  // (P1b) Agent 工作台已收敛进 DSH 任务，路由重定向 /dsh-tasks，入口不再单列
]

export function filterCommandRoutes(
  routes: CommandRoute[],
  hasPerm: (code: string) => boolean,
  visibleMenuPaths?: ReadonlySet<string>,
  aitdeEnabled = true,
): CommandRoute[] {
  return routes.filter((route) => {
    if (route.permission && !hasPerm(route.permission)) return false
    // menuBacked 条目跟随菜单可见性（DISABLED_MENUS 软下线即隐藏）；
    // 未传菜单路径集合时保持旧行为（仅按权限过滤），兼容既有调用方。
    if (route.menuBacked && visibleMenuPaths && !visibleMenuPaths.has(route.path)) return false
    // AITDE 未开启时不列出主链入口，避免搜到就跳进「未开放」占位页。
    if (route.requiresAitde && !aitdeEnabled) return false
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
  const aitdeEnabled = useAitdeV3Enabled()

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
    const visible = filterCommandRoutes(ALL_COMMAND_ROUTES, hasPerm, visibleMenuPaths, aitdeEnabled)
    return visible.filter((r) => matchesQuery(r, query))
  }, [query, hasPerm, visibleMenuPaths, aitdeEnabled])

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
