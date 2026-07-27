/**
 * LoadingState — Three-variant loading indicator.
 *
 * - skeleton (default): Reuses existing SkeletonTable/SkeletonCard/SkeletonPage
 *   from @/components/ui/skeleton for content-placeholder patterns.
 * - spinner: Centered animated Loader2 spinner with optional text.
 * - inline: Compact spinner + text for button/action loading contexts.
 */

import { Loader2 } from '@/lib/icons'
import { cn } from '@/lib/utils'
import {
  Skeleton,
  SkeletonCircle,
  SkeletonTable,
  SkeletonCard,
  SkeletonPage,
} from '@/components/ui/skeleton'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type LoadingVariant = 'skeleton' | 'spinner' | 'inline'
export type LoadingSize = 'sm' | 'md' | 'lg'

export interface LoadingStateProps {
  /** Visual variant. @default 'skeleton' */
  variant?: LoadingVariant
  /** Size preset controlling spacing / icon scale. @default 'md' */
  size?: LoadingSize
  /** Skeleton context hint. @default 'table' */
  skeletonType?: 'table' | 'card' | 'page' | 'form'
  /** Rows for table/card skeleton. @default 5 */
  rows?: number
  /** Columns for table skeleton. @default 4 */
  columns?: number
  /** Optional text shown below spinner. */
  text?: string
  /** When true, container fills viewport height (centered). @default false */
  fullPage?: boolean
  /** Additional CSS classes. */
  className?: string
}

// ---------------------------------------------------------------------------
// Size presets
// ---------------------------------------------------------------------------

const sizeClasses: Record<LoadingSize, { icon: string; container: string }> = {
  sm: { icon: 'size-4', container: 'py-4 gap-2' },
  md: { icon: 'size-8', container: 'py-12 gap-3' },
  lg: { icon: 'size-12', container: 'py-20 gap-4' },
}

// ---------------------------------------------------------------------------
// Form skeleton (internal — not yet exported from skeleton.tsx)
// ---------------------------------------------------------------------------

function SkeletonForm({
  rows = 4,
  className,
}: {
  rows?: number
  className?: string
}) {
  // Varying label widths to look natural
  const labelWidths = ['w-16', 'w-20', 'w-14', 'w-24', 'w-18', 'w-22']
  return (
    <div className={cn('space-y-4', className)}>
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="space-y-2">
          <Skeleton className={cn('h-4', labelWidths[i % labelWidths.length])} />
          <Skeleton className="h-9 w-full rounded-md" />
        </div>
      ))}
      <Skeleton className="h-9 w-24 rounded-lg" />
    </div>
  )
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function LoadingState({
  variant = 'skeleton',
  size = 'md',
  skeletonType = 'table',
  rows = 5,
  columns = 4,
  text,
  fullPage = false,
  className,
}: LoadingStateProps) {
  // ── Skeleton variant ────────────────────────────────────────────
  if (variant === 'skeleton') {
    const containerClasses = cn(fullPage && 'min-h-[60vh] flex items-center', className)

    const skeletonEl = (() => {
      switch (skeletonType) {
        case 'card':
          return (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 w-full">
              {Array.from({ length: rows }).map((_, i) => (
                <SkeletonCard key={i} />
              ))}
            </div>
          )
        case 'page':
          return <SkeletonPage />
        case 'form':
          return <SkeletonForm rows={rows} />
        case 'table':
        default:
          return <SkeletonTable rows={rows} cols={columns} />
      }
    })()

    return (
      <div
        className={containerClasses}
        role="status"
        aria-label="加载中"
        aria-busy="true"
        aria-live="polite"
      >
        {skeletonEl}
      </div>
    )
  }

  // ── Spinner variant ─────────────────────────────────────────────
  if (variant === 'spinner') {
    const { icon, container } = sizeClasses[size]

    return (
      <div
        role="status"
        aria-label={text || '加载中'}
        aria-live="polite"
        className={cn(
          'flex flex-col items-center justify-center',
          container,
          fullPage && 'min-h-[60vh]',
          className,
        )}
      >
        <Loader2
          className={cn('animate-spin text-muted-foreground', icon)}
        />
        {text && (
          <p className="text-sm text-muted-foreground">{text}</p>
        )}
      </div>
    )
  }

  // ── Inline variant ──────────────────────────────────────────────
  return (
    <span
      role="status"
      aria-label={text || '加载中'}
      aria-live="polite"
      className={cn('inline-flex items-center', className)}
    >
      <Loader2 className="animate-spin size-4 inline-block align-middle text-muted-foreground" />
      {text && (
        <span className="ml-2 text-sm text-muted-foreground align-middle">
          {text}
        </span>
      )}
    </span>
  )
}

export default LoadingState
