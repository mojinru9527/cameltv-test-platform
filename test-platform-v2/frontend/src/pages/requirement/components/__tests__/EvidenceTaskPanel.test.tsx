import { act, cleanup, render } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const mockFetchJobs = vi.fn()
const mockToastError = vi.fn()

vi.mock('@/api/lanhuEvidence', () => ({
  fetchLanhuEvidenceJobs: (...args: unknown[]) => mockFetchJobs(...args),
  cancelLanhuEvidenceJob: vi.fn(),
  retryLanhuEvidenceJob: vi.fn(),
  deleteLanhuEvidenceJob: vi.fn(),
}))

vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: (...args: unknown[]) => mockToastError(...args),
  },
}))

const { default: EvidenceTaskPanel } = await import('../EvidenceTaskPanel')

function job(status: string) {
  return {
    id: 1,
    status,
    stage: status === 'running' ? 'capturing' : 'done',
    source_url: 'https://lanhu.example/updates/1.0',
    total_pages: 2,
    captured_pages: status === 'running' ? 1 : 2,
    attempt_no: 1,
    created_at: new Date().toISOString(),
    import_result_json: '{}',
  }
}

function deferred<T>() {
  let resolve!: (value: T) => void
  const promise = new Promise<T>((resolver) => {
    resolve = resolver
  })
  return { promise, resolve }
}

describe('EvidenceTaskPanel polling', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.clearAllMocks()
  })

  afterEach(() => {
    cleanup()
    vi.useRealTimers()
  })

  it('stops polling after all jobs reach a terminal state', async () => {
    mockFetchJobs.mockResolvedValue({ items: [job('success')] })

    render(<EvidenceTaskPanel />)
    await act(async () => { await Promise.resolve() })
    expect(mockFetchJobs).toHaveBeenCalledTimes(1)

    await act(async () => { await vi.advanceTimersByTimeAsync(12_000) })
    expect(mockFetchJobs).toHaveBeenCalledTimes(1)
  })

  it('never overlaps requests while an active job is being polled', async () => {
    const second = deferred<{ items: ReturnType<typeof job>[] }>()
    mockFetchJobs
      .mockResolvedValueOnce({ items: [job('running')] })
      .mockReturnValueOnce(second.promise)

    render(<EvidenceTaskPanel />)
    await act(async () => { await Promise.resolve() })

    await act(async () => { await vi.advanceTimersByTimeAsync(3_000) })
    expect(mockFetchJobs).toHaveBeenCalledTimes(2)

    await act(async () => { await vi.advanceTimersByTimeAsync(12_000) })
    expect(mockFetchJobs).toHaveBeenCalledTimes(2)

    await act(async () => {
      second.resolve({ items: [job('success')] })
      await Promise.resolve()
    })
    await act(async () => { await vi.advanceTimersByTimeAsync(6_000) })
    expect(mockFetchJobs).toHaveBeenCalledTimes(2)
  })

  it('aborts the in-flight request when unmounted', async () => {
    let signal: AbortSignal | undefined
    mockFetchJobs.mockImplementation(
      (_params: unknown, requestSignal: AbortSignal) => {
        signal = requestSignal
        return new Promise(() => {})
      },
    )

    const view = render(<EvidenceTaskPanel />)
    await act(async () => { await Promise.resolve() })
    expect(mockFetchJobs).toHaveBeenCalledTimes(1)
    view.unmount()

    expect(signal?.aborted).toBe(true)
  })

  it('backs off failed polling at 3, 6, 12 and 30 seconds', async () => {
    mockFetchJobs.mockRejectedValue(new Error('network unavailable'))

    render(<EvidenceTaskPanel />)
    await act(async () => { await Promise.resolve() })
    expect(mockFetchJobs).toHaveBeenCalledTimes(1)

    await act(async () => { await vi.advanceTimersByTimeAsync(2_999) })
    expect(mockFetchJobs).toHaveBeenCalledTimes(1)
    await act(async () => { await vi.advanceTimersByTimeAsync(1) })
    expect(mockFetchJobs).toHaveBeenCalledTimes(2)

    await act(async () => { await vi.advanceTimersByTimeAsync(5_999) })
    expect(mockFetchJobs).toHaveBeenCalledTimes(2)
    await act(async () => { await vi.advanceTimersByTimeAsync(1) })
    expect(mockFetchJobs).toHaveBeenCalledTimes(3)

    await act(async () => { await vi.advanceTimersByTimeAsync(11_999) })
    expect(mockFetchJobs).toHaveBeenCalledTimes(3)
    await act(async () => { await vi.advanceTimersByTimeAsync(1) })
    expect(mockFetchJobs).toHaveBeenCalledTimes(4)

    await act(async () => { await vi.advanceTimersByTimeAsync(29_999) })
    expect(mockFetchJobs).toHaveBeenCalledTimes(4)
    await act(async () => { await vi.advanceTimersByTimeAsync(1) })
    expect(mockFetchJobs).toHaveBeenCalledTimes(5)
  })

  it('reports the first polling failure once without a toast storm', async () => {
    mockFetchJobs.mockRejectedValue(new Error('network unavailable'))

    render(<EvidenceTaskPanel />)
    await act(async () => { await Promise.resolve() })
    await act(async () => { await vi.advanceTimersByTimeAsync(45_000) })

    expect(mockToastError).toHaveBeenCalledTimes(1)
  })
})
