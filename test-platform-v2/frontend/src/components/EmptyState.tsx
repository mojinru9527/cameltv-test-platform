import type { LucideIcon } from 'lucide-react'
import { Inbox } from '@/lib/icons'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface EmptyStateProps {
  /** Icon component (from lucide-react). @default Inbox */
  icon?: LucideIcon
  /** Required title text. */
  title: string
  /** Optional description text. */
  description?: string
  /** Optional action button. */
  action?: {
    label: string
    onClick: () => void
  }
  /** Size preset. @default 'md' */
  size?: 'sm' | 'md' | 'lg'
  /** Visual variant. @default 'default' */
  variant?: 'default' | 'bordered'
  /** Children slot — rendered below the action button. */
  children?: React.ReactNode
  /** Additional CSS classes. */
  className?: string
}

// ---------------------------------------------------------------------------
// Size presets
// ---------------------------------------------------------------------------

const sizeConfig: Record<
  'sm' | 'md' | 'lg',
  {
    container: string
    iconWrap: string
    icon: string
    title: string
    descMaxW: string
  }
> = {
  sm: {
    container: 'py-8 px-4',
    iconWrap: 'p-3 mb-3',
    icon: 'size-6',
    title: 'text-sm',
    descMaxW: 'max-w-xs',
  },
  md: {
    container: 'py-16 px-4',
    iconWrap: 'p-4 mb-4',
    icon: 'size-8',
    title: 'text-base font-semibold',
    descMaxW: 'max-w-sm',
  },
  lg: {
    container: 'py-24 px-4',
    iconWrap: 'p-5 mb-5',
    icon: 'size-12',
    title: 'text-lg font-semibold',
    descMaxW: 'max-w-md',
  },
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function EmptyState({
  icon: Icon = Inbox,
  title,
  description,
  action,
  size = 'md',
  variant = 'default',
  children,
  className,
}: EmptyStateProps) {
  const s = sizeConfig[size]

  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center text-center',
        s.container,
        variant === 'bordered' &&
          'border-2 border-dashed border-border rounded-xl',
        className,
      )}
    >
      <div className={cn('rounded-full bg-muted', s.iconWrap)}>
        <Icon className={cn('text-muted-foreground', s.icon)} aria-hidden="true" />
      </div>
      <h3 className={cn('mb-1', s.title)}>{title}</h3>
      {description && (
        <p
          className={cn(
            'text-sm text-muted-hc mb-4',
            s.descMaxW,
          )}
        >
          {description}
        </p>
      )}
      {action && (
        <Button onClick={action.onClick} size="sm">
          {action.label}
        </Button>
      )}
      {children && <div className="mt-4">{children}</div>}
    </div>
  )
}
