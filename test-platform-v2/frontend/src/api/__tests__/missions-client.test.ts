import { afterEach, describe, expect, it, vi } from 'vitest'
import { toast } from 'sonner'
import { aitdeV2 } from '../missions'

const errorHandler = aitdeV2.interceptors.response.handlers
  .map((handler) => (handler as { rejected?: unknown })?.rejected)
  .find((handler): handler is (error: any) => Promise<any> => typeof handler === 'function') ?? null

afterEach(() => {
  vi.restoreAllMocks()
})

describe('AITDE v2 client error handling', () => {
  it('does not show a toast when navigation cancels a request', async () => {
    expect(errorHandler).toBeTypeOf('function')
    const toastSpy = vi.spyOn(toast, 'error').mockImplementation(() => 'toast-id')
    const canceled = Object.assign(new Error('canceled'), { code: 'ERR_CANCELED' })

    await expect(errorHandler!(canceled)).rejects.toBe(canceled)

    expect(toastSpy).not.toHaveBeenCalled()
  })

  it('keeps ordinary transport failures visible', async () => {
    const toastSpy = vi.spyOn(toast, 'error').mockImplementation(() => 'toast-id')
    const failure = Object.assign(new Error('网络断开'), { config: {} })

    await expect(errorHandler!(failure)).rejects.toBe(failure)

    expect(toastSpy).toHaveBeenCalledWith('网络断开')
  })
})
