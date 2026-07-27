/**
 * ErrorState — Error display with retry action and collapsible details.
 *
 * Shows an AlertTriangle icon, error summary, optional retry button,
 * optional secondary action, and a collapsible details panel for
 * debugging (collapsed by default).
 */

import { useState } from 'react'
import { AlertTriangle, ChevronDown } from '@/lib/icons'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface ErrorStateProps {
  /** Error summary heading. @default "加载失败" */
  title?: string
  /** Supplementary description shown below the title. */
  description?: string
  /** Error object whose message is used as description and shown in details. */
  error?: Error | string | null
  /** Retry callback. When provided, a "重试" button is rendered. */
  onRetry?: () => void
  /** Optional secondary action button (e.g. "返回首页"). */
  secondaryAction?: {
    label: string
    onClick: () => void
  }
  /** Explicitly show/hide the details panel. When undefined, auto-detects
   * based on whether there is detail content to show. */
  showDetails?: boolean
  /** Custom details content. Falls back to error.message + error.stack. */
  details?: string
  /** When true, container fills viewport height (centered). @default false */
  fullPage?: boolean
  /** Additional CSS classes. */
  className?: string
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function normalizeError(err: Error | string | null): {
  message: string
  stack: string
} {
  if (!err) return { message: '', stack: '' }
  if (typeof err === 'string') return { message: err, stack: '' }
  return {
    message: err.message || '',
    stack: err.stack || '',
  }
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function ErrorState({
  title = '加载失败',
  description,
  error,
  onRetry,
  secondaryAction,
  showDetails,
  details,
  fullPage = false,
  className,
}: ErrorStateProps) {
  const [isOpen, setIsOpen] = useState(false)

  const err = normalizeError(error ?? null)

  // Determine whether to show the details panel.
  const hasDetails =
    showDetails ??
    (!!details || !!err.message)

  const body =
    details || [err.message, err.stack].filter(Boolean).join('\n\n') || ''

  // Default description falls back to a truncated error message.
  const displayDescription =
    description ||
    (err.message ? (err.message.length > 120 ? err.message.slice(0, 120) + '...' : err.message) : undefined)

  return (
    <div
      role="alert"
      className={cn(
        'flex flex-col items-center justify-center text-center',
        fullPage ? 'min-h-[60vh]' : 'py-16',
        'px-4',
        className,
      )}
    >
      {/* Icon */}
      <div className="rounded-full bg-destructive/10 p-3 mb-4">
        <AlertTriangle
          className="size-10 text-destructive/70"
          aria-hidden="true"
        />
      </div>

      {/* Title */}
      <h3 className="text-base font-semibold mb-1">{title}</h3>

      {/* Description */}
      {displayDescription && (
        <p className="text-sm text-muted-foreground max-w-sm mb-4 text-center">
          {displayDescription}
        </p>
      )}

      {/* Actions */}
      {(onRetry || secondaryAction) && (
        <div className="flex items-center gap-2 mb-4">
          {onRetry && (
            <Button
              variant="outline"
              size="sm"
              onClick={onRetry}
              aria-label="重新加载"
            >
              重试
            </Button>
          )}
          {secondaryAction && (
            <Button
              variant="ghost"
              size="sm"
              onClick={secondaryAction.onClick}
            >
              {secondaryAction.label}
            </Button>
          )}
        </div>
      )}

      {/* Collapsible error details */}
      {hasDetails && (
        <Collapsible open={isOpen} onOpenChange={setIsOpen}>
          <CollapsibleTrigger asChild>
            <Button
              variant="ghost"
              size="sm"
              className="text-xs text-muted-foreground"
              aria-expanded={isOpen}
            >
              <ChevronDown
                className={cn(
                  'size-3 mr-1 transition-transform',
                  isOpen && 'rotate-180',
                )}
                aria-hidden="true"
              />
              {isOpen ? '收起详情' : '查看详情'}
            </Button>
          </CollapsibleTrigger>
          <CollapsibleContent>
            <pre
              className="mt-2 p-3 rounded-md bg-muted text-xs font-mono text-muted-foreground overflow-auto max-h-48 whitespace-pre-wrap text-left"
              aria-label="错误详情"
            >
              {body}
            </pre>
          </CollapsibleContent>
        </Collapsible>
      )}
    </div>
  )
}

export default ErrorState
