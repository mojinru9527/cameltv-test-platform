/**
 * AsyncState — Declarative container that composes LoadingState, ErrorState,
 * and EmptyState based on the results returned by the useApi hook.
 *
 * @example
 * const { data, isLoading, isError, error, refetch } = useApi(
 *   (signal) => fetchTestCases({ status, signal }),
 *   [status]
 * )
 *
 * return (
 *   <AsyncState
 *     isLoading={isLoading}
 *     isError={isError}
 *     error={error}
 *     data={data}
 *     onRetry={refetch}
 *     emptyTitle="暂无测试用例"
 *     emptyAction={{ label: '创建用例', onClick: () => openDrawer() }}
 *   >
 *     {(items) => <DataTable data={items} />}
 *   </AsyncState>
 * )
 */

import type { LucideIcon } from '@/lib/icons'

import { LoadingState, type LoadingStateProps } from './LoadingState'
import { ErrorState } from './ErrorState'
import EmptyState from '@/components/EmptyState'
import { cn } from '@/lib/utils'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface AsyncStateProps<T> {
  // ── State values (typically from useApi) ─────────────────────────

  isLoading: boolean
  isError: boolean
  error: Error | null
  data: T | undefined

  // ── Loading configuration ────────────────────────────────────────

  /** Override loading variant. Defaults to 'spinner' for first load. */
  loadingVariant?: LoadingStateProps['variant']
  /** Rows for skeleton. @default 5 */
  loadingRows?: number
  /** Skeleton type. @default 'table' */
  skeletonType?: LoadingStateProps['skeletonType']
  /** Loading text shown below spinner. */
  loadingText?: string

  // ── Empty configuration ──────────────────────────────────────────

  emptyTitle?: string
  emptyDescription?: string
  emptyIcon?: LucideIcon
  emptyAction?: { label: string; onClick: () => void }

  // ── Error configuration ──────────────────────────────────────────

  errorTitle?: string
  errorDescription?: string
  onRetry?: () => void

  // ── Styling ──────────────────────────────────────────────────────

  /** When true, loading/error containers fill viewport. */
  fullPage?: boolean
  /** Additional CSS classes. */
  className?: string

  // ── Content rendering ────────────────────────────────────────────

  /** Render function receiving non-null data, OR plain ReactNode. */
  children: ((data: NonNullable<T>) => React.ReactNode) | React.ReactNode
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function isDataEmpty<T>(data: T | undefined): boolean {
  if (data === undefined || data === null) return true
  if (Array.isArray(data) && data.length === 0) return true
  if (typeof data === 'object' && Object.keys(data as object).length === 0) return true
  return false
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function AsyncState<T>({
  isLoading,
  isError,
  error,
  data,

  loadingVariant = 'spinner',
  loadingRows = 5,
  skeletonType = 'table',
  loadingText,

  emptyTitle = '暂无数据',
  emptyDescription,
  emptyIcon,
  emptyAction,

  errorTitle,
  errorDescription,
  onRetry,

  fullPage,
  className,

  children,
}: AsyncStateProps<T>) {
  // ── 1. Loading (first load — no data yet) ─────────────────────
  if (isLoading && data === undefined) {
    return (
      <LoadingState
        variant={loadingVariant}
        skeletonType={skeletonType}
        rows={loadingRows}
        text={loadingText}
        fullPage={fullPage}
        className={className}
      />
    )
  }

  // ── 2. Error (no data) ────────────────────────────────────────
  if (isError && data === undefined) {
    return (
      <ErrorState
        title={errorTitle}
        description={errorDescription}
        error={error}
        onRetry={onRetry}
        fullPage={fullPage}
        className={className}
      />
    )
  }

  // ── 3. Empty data ─────────────────────────────────────────────
  if (!isLoading && !isError && isDataEmpty(data)) {
    return (
      <EmptyState
        icon={emptyIcon}
        title={emptyTitle}
        description={emptyDescription}
        action={emptyAction}
        className={className}
      />
    )
  }

  // ── 4. Data available — render children ───────────────────────
  const content =
    typeof children === 'function'
      ? (children as (data: NonNullable<T>) => React.ReactNode)(data as NonNullable<T>)
      : children

  return <div className={cn(className)}>{content}</div>
}

export default AsyncState
