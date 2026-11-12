import { NavLink } from 'react-router'
import { cn } from '@/lib/utils'

/** AIQE Console 页签（batch-337）：执行记录 / Execution Profiles / Workflow 审批。 */
const TABS = [
  { to: '/runs', label: '执行记录' },
  { to: '/aiqe/profiles', label: 'Execution Profiles' },
  { to: '/aiqe/workflows', label: 'Workflow 审批' },
  { to: '/aiqe/quality-gate', label: '质量门禁' },
  { to: '/aiqe/noise-rules', label: '噪音规则' },
  { to: '/aiqe/platform-matrix', label: '平台矩阵' },
] as const

export default function ConsoleTabs() {
  return (
    <nav className="flex flex-wrap gap-1 border-b pb-2" aria-label="AIQE Console 导航">
      {TABS.map((tab) => (
        <NavLink
          key={tab.to}
          to={tab.to}
          end={tab.to === '/runs'}
          className={({ isActive }) =>
            cn(
              'rounded px-3 py-1.5 text-sm transition-colors',
              isActive
                ? 'bg-muted font-medium text-foreground'
                : 'text-muted-foreground hover:bg-muted/60',
            )
          }
        >
          {tab.label}
        </NavLink>
      ))}
    </nav>
  )
}
