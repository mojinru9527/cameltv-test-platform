import { type ReactNode } from 'react'
import { cn } from '@/lib/utils'

export interface PageShellProps {
  /** 页面标题 */
  title?: string
  /** 面包屑路径 */
  breadcrumbs?: string
  /** 副标题描述 */
  description?: string
  /** 标题右侧操作区 */
  actions?: ReactNode
  /** 状态栏（如环境、同步时间） */
  statusLine?: ReactNode
  /** 页面内容 */
  children: ReactNode
  /** 是否为玻璃材质顶栏 */
  glass?: boolean
  className?: string
}

export function PageShell({
  title,
  breadcrumbs,
  description,
  actions,
  statusLine,
  children,
  glass = false,
  className,
}: PageShellProps) {
  return (
    <div className={cn('flex flex-col gap-6', className)}>
      {/* ── 页头 ── */}
      {(title || breadcrumbs || actions) && (
        <header className={cn(glass && 'ui-glass p-4')}>
          {breadcrumbs && (
            <span className="block mb-2 text-[0.8125rem] text-[#829087]">
              {breadcrumbs}
            </span>
          )}
          <div className="flex items-center justify-between gap-8">
            <div className="min-w-0">
              {title && (
                <h1 className="text-[clamp(1.75rem,2.4vw,2.25rem)] font-[580] tracking-tight leading-[1.08] text-[#f5faf6] text-balance">
                  {title}
                </h1>
              )}
              {description && (
                <p className="mt-4 max-w-[70ch] text-[1rem] leading-relaxed text-[#a7b5ab]">
                  {description}
                </p>
              )}
            </div>
            {actions && (
              <div className="flex flex-shrink-0 gap-2">{actions}</div>
            )}
          </div>
          {statusLine && (
            <div className="flex items-center gap-4 mt-4 text-[0.8125rem] text-[#819086]">
              {statusLine}
            </div>
          )}
        </header>
      )}

      {/* ── 内容 ── */}
      {children}
    </div>
  )
}
