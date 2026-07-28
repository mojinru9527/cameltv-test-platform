import { type ReactNode } from 'react'
import { cn } from '@/lib/utils'

export interface PageShellProps {
  /** 页面标题 */
  title: string
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
    <div className={cn('flex min-w-0 flex-col gap-4 sm:gap-6', className)}>
      <header
        className={cn(
          'rounded-xl border border-border bg-card px-4 py-4 text-card-foreground sm:px-5',
          glass && 'ui-glass',
        )}
      >
        {breadcrumbs && (
          <p className="mb-2 text-sm text-muted-hc">{breadcrumbs}</p>
        )}
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div className="min-w-0">
            <h1 className="text-xl font-semibold leading-tight tracking-[-0.02em] text-foreground text-balance sm:text-2xl">
              {title}
            </h1>
            {description && (
              <p className="mt-2 max-w-[70ch] text-sm leading-relaxed text-muted-hc text-pretty">
                {description}
              </p>
            )}
          </div>
          {actions && (
            <div
              data-testid="page-shell-actions"
              className="flex w-full flex-wrap items-center gap-2 sm:w-auto sm:flex-shrink-0 sm:justify-end"
            >
              {actions}
            </div>
          )}
        </div>
        {statusLine && (
          <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-2 text-sm text-muted-hc">
            {statusLine}
          </div>
        )}
      </header>

      <div className="min-w-0">{children}</div>
    </div>
  )
}
