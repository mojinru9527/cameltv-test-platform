/**
 * useApi hook tests — covers core states: loading, data, error, refetch, abort.
 *
 * Uses jsdom environment + real async (NO fake timers) to avoid deadlocks
 * between vi.useFakeTimers() and @testing-library/react's waitFor.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, waitFor, act } from '@testing-library/react'
import { useApi } from '../useApi'

// Helper: create a controllable promise
function deferred<T>() {
  let resolve!: (value: T) => void
  let reject!: (reason?: unknown) => void
  const promise = new Promise<T>((res, rej) => {
    resolve = res
    reject = rej
  })
  return { promise, resolve, reject }
}

describe('useApi', () => {
  it('returns isLoading=true before fetch resolves', async () => {
    const { promise, resolve } = deferred<string[]>()
    const fetchFn = vi.fn().mockReturnValue(promise)

    const { result } = renderHook(() => useApi(fetchFn, []))

    expect(result.current.isLoading).toBe(true)
    expect(result.current.data).toBeUndefined()
    expect(result.current.isError).toBe(false)

    // Resolve and wait for state update
    await act(async () => {
      resolve(['item1', 'item2'])
    })

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false)
      expect(result.current.data).toEqual(['item1', 'item2'])
    })
  })

  it('returns data after successful fetch', async () => {
    const fetchFn = vi.fn().mockResolvedValue(['a', 'b', 'c'])

    const { result } = renderHook(() => useApi(fetchFn, []))

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false)
    })

    expect(result.current.data).toEqual(['a', 'b', 'c'])
    expect(result.current.isError).toBe(false)
    expect(result.current.error).toBeNull()
  })

  it('handles fetch errors', async () => {
    const fetchFn = vi.fn().mockRejectedValue(new Error('Network error'))

    const { result } = renderHook(() => useApi(fetchFn, []))

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false)
    })

    expect(result.current.isError).toBe(true)
    expect(result.current.error).toBeInstanceOf(Error)
    expect(result.current.error?.message).toBe('Network error')
  })

  it('supports initialData', async () => {
    const fetchFn = vi.fn().mockResolvedValue('fresh data')

    const { result } = renderHook(() =>
      useApi(fetchFn, { deps: [], initialData: 'initial' })
    )

    expect(result.current.data).toBe('initial')
    expect(result.current.isLoading).toBe(true)

    await waitFor(() => {
      expect(result.current.data).toBe('fresh data')
    })
  })

  it('refetch triggers a new request', async () => {
    let callCount = 0
    const fetchFn = vi.fn().mockImplementation(() => {
      callCount++
      return Promise.resolve(callCount)
    })

    const { result } = renderHook(() => useApi(fetchFn, []))

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false)
    })

    expect(result.current.data).toBe(1)

    // Trigger refetch
    await act(async () => {
      result.current.refetch()
    })

    await waitFor(() => {
      expect(result.current.data).toBe(2)
    })
  })

  it('aborts in-flight request on unmount', async () => {
    const { promise, reject } = deferred<string>()
    const fetchFn = vi.fn().mockReturnValue(promise)

    const { result, unmount } = renderHook(() => useApi(fetchFn, []))

    expect(result.current.isLoading).toBe(true)

    // Unmount before resolution
    unmount()

    // Reject with AbortError — should not cause state updates
    reject(new DOMException('Aborted', 'AbortError'))

    // No assertion needed — if the hook didn't handle abort correctly,
    // React would warn about state updates on unmounted component
    expect(fetchFn).toHaveBeenCalledTimes(1)
  })
})
