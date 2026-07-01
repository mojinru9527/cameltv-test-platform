import { useEffect, useState, useCallback, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
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
  Search,
  GitBranch,
  Share2,
  type LucideIcon,
} from '@/lib/icons'

// Route registry — all searchable pages
const STATIC_ROUTES: { label: string; path: string; icon: LucideIcon; group: string }[] = [
  { label: '工作台', path: '/workbench', icon: LayoutDashboard, group: '页面' },
  { label: '用例服务', path: '/testcase', icon: FileText, group: '页面' },
  { label: '测试计划', path: '/testplan', icon: FolderOpen, group: '页面' },
  { label: '需求管理', path: '/requirement', icon: GitBranch, group: '页面' },
  { label: '报告中心', path: '/report', icon: BarChart3, group: '页面' },
  { label: '定时任务', path: '/schedule', icon: Clock, group: '页面' },
  { label: '缺陷管理', path: '/defect', icon: Bug, group: '页面' },
  { label: '质量追溯', path: '/trace', icon: Share2, group: '页面' },
  { label: '项目管理', path: '/project', icon: Settings, group: '页面' },
  { label: '系统管理', path: '/system', icon: Settings, group: '页面' },
  { label: 'API 测试', path: '/apitest', icon: FileText, group: '页面' },
  { label: 'UI 自动化', path: '/uitest', icon: FileText, group: '页面' },
  { label: '音视频专项', path: '/special', icon: FileText, group: '页面' },
]

export default function CommandPalette() {
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')

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
    if (!query.trim()) return STATIC_ROUTES
    const q = query.toLowerCase()
    return STATIC_ROUTES.filter(
      (r) =>
        r.label.toLowerCase().includes(q) ||
        r.path.toLowerCase().includes(q) ||
        r.group.toLowerCase().includes(q),
    )
  }, [query])

  const groups = useMemo(() => {
    const map = new Map<string, typeof STATIC_ROUTES>()
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
