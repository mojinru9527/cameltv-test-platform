import { act, renderHook } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { useDebouncedValue } from '../useDebouncedValue'

describe('useDebouncedValue（Batch 150 / C147-5）', () => {
  afterEach(() => {
    vi.useRealTimers()
  })

  it('输入变化后延迟 300ms 才更新', () => {
    vi.useFakeTimers()
    const { result, rerender } = renderHook(
      ({ v }) => useDebouncedValue(v, 300),
      { initialProps: { v: 'a' } },
    )
    expect(result.current).toBe('a')

    rerender({ v: 'ab' })
    expect(result.current).toBe('a')

    act(() => { vi.advanceTimersByTime(300) })
    expect(result.current).toBe('ab')
  })
})
