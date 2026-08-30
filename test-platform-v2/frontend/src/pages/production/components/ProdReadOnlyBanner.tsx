import { AlertTriangle } from '@/lib/icons'
import { cn } from '@/lib/utils'

interface ProdReadOnlyBannerProps {
  className?: string
}

/**
 * Required banner shown on every production-evidence page. Renders the literal
 * text "PRODUCTION / READ ONLY" (not merely a colour cue) in warning styling.
 */
export function ProdReadOnlyBanner({ className }: ProdReadOnlyBannerProps) {
  return (
    <div
      role="status"
      data-testid="prod-read-only-banner"
      className={cn(
        'flex items-center gap-2 rounded-lg border border-status-danger bg-status-danger-muted px-3 py-2 text-sm font-semibold text-status-danger',
        className,
      )}
    >
      <AlertTriangle className="size-4 shrink-0" aria-hidden="true" />
      <span>PRODUCTION / READ ONLY</span>
    </div>
  )
}
