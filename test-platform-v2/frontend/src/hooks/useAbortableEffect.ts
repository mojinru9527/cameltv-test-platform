import { useEffect, useRef, type DependencyList } from 'react'

export function rethrowUnlessAborted(error: unknown, signal?: AbortSignal) {
  if (!signal?.aborted) throw error
}

/**
 * Runs an async side effect once per dependency change and aborts superseded work.
 *
 * Deferring setup by one microtask prevents React StrictMode's discarded mount
 * from issuing an effective request. The surviving setup still receives an
 * AbortSignal for dependency changes and real unmounts.
 */
export function useAbortableEffect(
  effect: (signal: AbortSignal) => void,
  dependencies: DependencyList,
) {
  const effectRef = useRef(effect)
  effectRef.current = effect

  useEffect(() => {
    const controller = new AbortController()
    let cancelled = false

    queueMicrotask(() => {
      if (!cancelled) effectRef.current(controller.signal)
    })

    return () => {
      cancelled = true
      controller.abort()
    }
    // The caller owns the dependency list, matching the native useEffect API.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, dependencies)
}

export default useAbortableEffect
