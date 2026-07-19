/**
 * usePaginatedList — Encapsulates the common CRUD list pattern used across
 * 6+ pages (testcase, testplan, defect, report, schedule, environment).
 *
 * Manages:
 *  - Filter state (generic record) with auto page-reset on filter change
 *  - Pagination (page, pageSize)
 *  - Data fetching via useApi with AbortController
 *  - Delete → toast → refetch cycle with AlertDialog state
 *
 * @example
 * const list = usePaginatedList({
 *   fetchFn: (signal, params) => fetchTestCases({ ...params, signal }),
 *   initialFilters: { status: '', keyword: '' },
 *   initialPageSize: 20,
 *   deleteFn: deleteTestCase,
 *   deleteLabel: (item) => item.title,
 * })
 *
 * // In JSX:
 * <AsyncState {...list.asyncState} emptyTitle="暂无数据" onRetry={list.refetch}>
 *   {(data) => (
 *     <DataTable
 *       columns={columns}
 *       data={data.items}
 *       rowKey={(r) => r.id}
 *       pagination={{
 *         page: data.page,
 *         totalPages: Math.ceil(data.total / data.page_size),
 *         total: data.total,
 *         onChange: list.setPage,
 *       }}
 *       toolbar={<Filters ... />}
 *     />
 *   )}
 * </AsyncState>
 */

import { useCallback, useRef, useState } from 'react'
import { toast } from 'sonner'
import useApi from './useApi'

// ── Types ────────────────────────────────────────────────

export interface PaginatedParams {
  page: number
  page_size: number
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

export interface UsePaginatedListOptions<TItem, TFilters extends Record<string, any>> {
  /** API fetch function. Receives AbortSignal + merged filter & pagination params. */
  fetchFn: (
    signal: AbortSignal,
    params: PaginatedParams & TFilters,
  ) => Promise<PaginatedResponse<TItem>>

  /** Initial filter values. Keys must match the fetchFn's params. */
  initialFilters: TFilters

  /** Items per page. @default 20 */
  initialPageSize?: number

  /** Optional delete function. Providing this enables `handleDelete`. */
  deleteFn?: (id: number) => Promise<any>

  /** Label extractor for delete confirmation toast. @default (item) => String(id) */
  deleteLabel?: (item: TItem) => string

  /** Extra deps that trigger a re-fetch (e.g. projectId changes). */
  deps?: any[]
}

export interface UsePaginatedListResult<TItem, TFilters extends Record<string, any>> {
  // ── Data ──
  data: PaginatedResponse<TItem> | undefined
  items: TItem[]
  isLoading: boolean
  isRefetching: boolean
  isError: boolean
  error: Error | null
  refetch: () => void

  // ── AsyncState props (for direct spreading) ──
  asyncState: {
    isLoading: boolean
    isError: boolean
    error: Error | null
    data: TItem[] | undefined
  }

  // ── Pagination ──
  page: number
  pageSize: number
  totalPages: number
  total: number
  setPage: (page: number) => void
  setPageSize: (size: number) => void

  // ── Filters ──
  filters: TFilters
  setFilter: <K extends keyof TFilters>(key: K, value: TFilters[K]) => void
  setFilters: (partial: Partial<TFilters>) => void
  resetFilters: () => void

  // ── Delete ──
  deleteTarget: number | null
  setDeleteTarget: (id: number | null) => void
  handleDelete: (id: number) => Promise<void>
  isDeleting: boolean
}

// ── Hook ─────────────────────────────────────────────────

export function usePaginatedList<TItem, TFilters extends Record<string, any>>(
  options: UsePaginatedListOptions<TItem, TFilters>,
): UsePaginatedListResult<TItem, TFilters> {
  const {
    fetchFn,
    initialFilters,
    initialPageSize = 20,
    deleteFn,
    deleteLabel = () => '',
    deps = [],
  } = options

  // ── State ──

  const [filters, setFiltersState] = useState<TFilters>(initialFilters)
  const [page, setPageState] = useState(1)
  const [pageSize, setPageSizeState] = useState(initialPageSize)

  // Delete
  const [deleteTarget, setDeleteTarget] = useState<number | null>(null)
  const [isDeleting, setIsDeleting] = useState(false)

  // Track previous filter signature to detect genuine changes
  const prevFilterSig = useRef<string>('')

  // ── Data fetching ──

  const { data, isLoading, isRefetching, isError, error, refetch: apiRefetch } = useApi(
    (signal) => fetchFn(signal, { page, page_size: pageSize, ...filters }),
    [page, pageSize, JSON.stringify(filters), ...deps],
  )

  // ── Page reset on filter change ──

  const setFilters = useCallback((partial: Partial<TFilters>) => {
    setFiltersState((prev) => {
      const next = { ...prev, ...partial }
      // Detect if filters actually changed (ignoring page-dependent fields)
      const sig = JSON.stringify(next)
      if (sig !== prevFilterSig.current) {
        prevFilterSig.current = sig
        setPageState(1)
      }
      return next
    })
  }, [])

  const setFilter = useCallback(<K extends keyof TFilters>(key: K, value: TFilters[K]) => {
    setFilters({ [key]: value } as unknown as Partial<TFilters>)
  }, [setFilters])

  const resetFilters = useCallback(() => {
    prevFilterSig.current = ''
    setFiltersState(initialFilters)
    setPageState(1)
  }, [initialFilters])

  const setPage = useCallback((p: number) => {
    setPageState(Math.max(1, p))
  }, [])

  const setPageSize = useCallback((size: number) => {
    setPageSizeState(size)
    setPageState(1)
  }, [])

  const refetch = useCallback(() => {
    apiRefetch()
  }, [apiRefetch])

  // ── Delete ──

  const handleDelete = useCallback(async (id: number) => {
    if (!deleteFn) return
    setIsDeleting(true)
    try {
      await deleteFn(id)
      toast.success('已删除')
      setDeleteTarget(null)
      refetch()
    } catch (err: any) {
      const msg = err?.detail || err?.message || '删除失败'
      toast.error(msg)
    } finally {
      setIsDeleting(false)
    }
  }, [deleteFn, refetch])

  // ── Derived values ──

  const items = (data?.items || []) as TItem[]
  const total = data?.total || 0
  const totalPages = data ? Math.max(1, Math.ceil(data.total / data.page_size)) : 1

  // asyncState for direct spreading into <AsyncState>
  const asyncState = {
    isLoading,
    isError,
    error,
    data: isError || isLoading ? undefined : items,
  }

  return {
    // Data
    data,
    items,
    isLoading,
    isRefetching,
    isError,
    error,
    refetch,

    // AsyncState spread
    asyncState,

    // Pagination
    page,
    pageSize,
    totalPages,
    total,
    setPage,
    setPageSize,

    // Filters
    filters,
    setFilter,
    setFilters,
    resetFilters,

    // Delete
    deleteTarget,
    setDeleteTarget,
    handleDelete,
    isDeleting,
  }
}

export default usePaginatedList
