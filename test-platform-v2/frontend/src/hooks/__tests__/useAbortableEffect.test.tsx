import { StrictMode } from 'react'
import { render, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import useAbortableEffect, { rethrowUnlessAborted } from '../useAbortableEffect'

function Harness({ request }: { request: (signal: AbortSignal) => void }) {
  useAbortableEffect(request, [request])
  return null
}

describe('useAbortableEffect', () => {
  it('starts one effective request during a React StrictMode mount', async () => {
    const request = vi.fn()

    render(
      <StrictMode>
        <Harness request={request} />
      </StrictMode>,
    )

    await waitFor(() => expect(request).toHaveBeenCalledTimes(1))
    expect(request.mock.calls[0][0].aborted).toBe(false)
  })

  it('aborts surviving work on unmount', async () => {
    const request = vi.fn()
    const view = render(<Harness request={request} />)
    await waitFor(() => expect(request).toHaveBeenCalledTimes(1))
    const signal = request.mock.calls[0][0]

    view.unmount()

    expect(signal.aborted).toBe(true)
  })

  it('swallows aborted request failures but preserves real failures', () => {
    const controller = new AbortController()
    const cancelled = new Error('request cancelled')
    controller.abort()

    expect(() => rethrowUnlessAborted(cancelled, controller.signal)).not.toThrow()
    expect(() => rethrowUnlessAborted(new Error('server failed'))).toThrow('server failed')
  })
})
