/**
 * useApi — Generic data-fetching hook with AbortController built-in.
 *
 * Manages loading / error / data states, supports dependency-driver refetch,
 * and separates "isLoading" (first fetch) from "isRefetching" (subsequent
 * background refresh).
 *
 * @example
 * const { data, isLoading, isError, error, refetch } = useApi(
 *   (signal) => fetchTestCases({ status, signal }),
 *   [status]
 * )
 */

import { useCallback, useEffect, useRef, useState } from 'react'
import { toast } from 'sonner'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface UseApiOptions<T> {
  /** Dependencies that trigger a re-fetch when changed. */
  deps?: any[]
  /** Initial value for `data` before the first fetch resolves. */
  initialData?: T
  /** Whether to show a sonner toast on fetch error. Default: true. */
  showErrorToast?: boolean
  /** Called after a successful fetch with the returned data. */
  onSuccess?: (data: T) => void
  /** Called after a failed fetch with the error. */
  onError?: (error: Error) => void
}

export interface UseApiResult<T> {
  data: T | undefined
  /** True only while the very first fetch is in flight (data is still undefined). */
  isLoading: boolean
  /** True when a refetch is in flight while stale data is still available. */
  isRefetching: boolean
  isError: boolean
  error: Error | null
  /** Manually trigger a re-fetch (cancels any in-flight request first). */
  refetch: () => void
  /** Overwrite data imperatively (optimistic updates, local mutations). */
  setData: (data: T | undefined) => void
  /** Abort the current in-flight request (if any). */
  abort: () => void
}

// ---------------------------------------------------------------------------
// Hook implementation
// ---------------------------------------------------------------------------

export function useApi<T>(
  fetchFn: (signal: AbortSignal) => Promise<T>,
  options?: UseApiOptions<T>,
): UseApiResult<T>

/**
 * Overload: passing deps as a positional array (simpler API for the common
 * case). Equivalent to `useApi(fetchFn, { deps })`.
 */
export function useApi<T>(
  fetchFn: (signal: AbortSignal) => Promise<T>,
  deps?: any[],
): UseApiResult<T>

export function useApi<T>(
  fetchFn: (signal: AbortSignal) => Promise<T>,
  depsOrOptions?: any[] | UseApiOptions<T>,
): UseApiResult<T> {
  const options: UseApiOptions<T> =
    Array.isArray(depsOrOptions) || depsOrOptions === undefined
      ? { deps: depsOrOptions }
      : depsOrOptions

  const {
    deps = [],
    initialData,
    showErrorToast = true,
    onSuccess,
    onError,
  } = options

  const [data, setData] = useState<T | undefined>(initialData)
  const [isLoading, setIsLoading] = useState(true)
  const [isRefetching, setIsRefetching] = useState(false)
  const [isError, setIsError] = useState(false)
  const [error, setError] = useState<Error | null>(null)

  // Track whether the very first fetch has ever completed — used to decide
  // between isLoading (first load) and isRefetching (background refresh).
  const hasLoadedOnce = useRef(false)

  // AbortController ref — replaced on every new request.
  const controllerRef = useRef<AbortController | null>(null)

  // Keep a stable reference to the fetch function via ref to avoid stale
  // closures inside the effect when the caller passes an inline arrow.
  const fetchFnRef = useRef(fetchFn)
  fetchFnRef.current = fetchFn

  // Track the previous deps so we can detect genuine changes and avoid
  // double-fires in Strict Mode.
  const depsRef = useRef<any[]>(deps)

  // -------------------------------------------------------------------
  // Core fetch logic
  // -------------------------------------------------------------------

  const execute = useCallback(() => {
    // Cancel any in-flight request before starting a new one.
    controllerRef.current?.abort()

    const controller = new AbortController()
    controllerRef.current = controller

    // Decide which loading flag to set based on whether we've ever loaded.
    if (hasLoadedOnce.current) {
      setIsRefetching(true)
    } else {
      setIsLoading(true)
    }
    setIsError(false)
    setError(null)

    fetchFnRef.current(controller.signal)
      .then((result) => {
        // Guard: component unmounted or a newer request superseded us.
        if (controller.signal.aborted) return

        setData(result)
        setIsLoading(false)
        setIsRefetching(false)
        setIsError(false)
        setError(null)
        hasLoadedOnce.current = true
        onSuccess?.(result)
      })
      .catch((err: unknown) => {
        // AbortError is expected — don't treat it as a real error.
        if (err instanceof DOMException && err.name === 'AbortError') return

        const errorObj = err instanceof Error ? err : new Error(String(err))

        if (controller.signal.aborted) return

        setIsLoading(false)
        setIsRefetching(false)
        setIsError(true)
        setError(errorObj)

        if (showErrorToast) {
          toast.error(errorObj.message || '请求失败，请稍后重试')
        }

        onError?.(errorObj)
      })
  }, [showErrorToast, onSuccess, onError])

  // -------------------------------------------------------------------
  // Trigger fetch on mount and when deps change.
  // -------------------------------------------------------------------

  useEffect(() => {
    // Compare deps with previous value to avoid Strict Mode double-fire.
    const prev = depsRef.current
    const changed =
      prev.length !== deps.length ||
      prev.some((v, i) => !Object.is(v, deps[i]))

    depsRef.current = deps

    if (changed) {
      execute()
    }

    // Cleanup: abort on unmount.
    return () => {
      controllerRef.current?.abort()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [execute, ...deps])

  // If deps were unchanged on mount, still fire the initial request.
  // This handles the case where the component mounts and the deps have
  // not "changed" (the effect above skips when deps match the initial
  // ref value). We use a separate effect that fires exactly once on mount.
  const didInitialFetch = useRef(false)
  useEffect(() => {
    if (!didInitialFetch.current) {
      didInitialFetch.current = true
      // Only fire if the main effect didn't already fire because deps changed.
      // The main effect runs after this one (same tick), but since it also
      // checks a ref that starts empty, the changed check is true on first
      // mount (prev.length is 0, deps.length might be 0 or N).  For zero-
      // length deps arrays on first mount, prev is [] (empty) and deps is
      // also [] — so changed = false and the main effect skips. This second
      // effect handles that case.
      const prev = depsRef.current
      const depsArr = deps as any[]
      const changed =
        prev.length !== depsArr.length ||
        prev.some((v, i) => !Object.is(v, depsArr[i]))
      if (!changed) {
        execute()
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // -------------------------------------------------------------------
  // Public API
  // -------------------------------------------------------------------

  const refetch = useCallback(() => {
    execute()
  }, [execute])

  const abort = useCallback(() => {
    controllerRef.current?.abort()
  }, [])

  return {
    data,
    isLoading,
    isRefetching,
    isError,
    error,
    refetch,
    setData,
    abort,
  }
}

export default useApi
