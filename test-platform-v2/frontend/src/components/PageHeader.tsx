import type { LucideIcon } from 'lucide-react'
import { cn } from '@/lib/utils'

interface PageHeaderProps {
  title: string
  icon?: LucideIcon
  description?: string
  children?: React.ReactNode
  className?: string
}

export default function PageHeader({ title, icon: Icon, description, children, className }: PageHeaderProps) {
  return (
    <div className={cn('flex items-center justify-between flex-wrap gap-2', className)}>
      <div>
        <h1 className="text-page font-semibold tracking-[-0.03em] flex items-center gap-2">
          {Icon && <Icon className="size-5" />}
          {title}
        </h1>
        {description && (
          <p className="text-sm text-muted-hc mt-0.5">{description}</p>
        )}
      </div>
      {children && <div className="flex items-center gap-2">{children}</div>}
    </div>
  )
}
