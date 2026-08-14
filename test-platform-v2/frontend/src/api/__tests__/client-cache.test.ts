import { afterEach, describe, expect, it, vi } from 'vitest'
import client, { cachedGet, clearApiCache } from '../client'

describe('cachedGet 会话级缓存与去重（Batch 150 / C147-5）', () => {
  afterEach(() => {
    vi.restoreAllMocks()
    clearApiCache()
  })

  it('命中缓存不重复请求', async () => {
    const get = vi.spyOn(client, 'get').mockResolvedValue([{ id: 1 }])
    const a = await cachedGet('/test', { p: 1 }, { ttl: 60_000 })
    const b = await cachedGet('/test', { p: 1 }, { ttl: 60_000 })
    expect(a).toEqual([{ id: 1 }])
    expect(b).toEqual([{ id: 1 }])
    expect(get).toHaveBeenCalledTimes(1)
  })

  it('进行中请求去重：并发共享同一 Promise', async () => {
    let resolveFn: ((v: unknown) => void) | undefined
    const get = vi.spyOn(client, 'get').mockImplementation(
      () => new Promise((resolve) => { resolveFn = resolve }) as any,
    )
    const p1 = cachedGet('/dup')
    const p2 = cachedGet('/dup')
    resolveFn!([{ id: 2 }])
    const [r1, r2] = await Promise.all([p1, p2])
    expect(get).toHaveBeenCalledTimes(1)
    expect(r1).toEqual([{ id: 2 }])
    expect(r2).toEqual([{ id: 2 }])
  })

  it('clearApiCache(prefix) 使缓存失效', async () => {
    const get = vi.spyOn(client, 'get').mockResolvedValue([{ id: 1 }])
    await cachedGet('/x', undefined, { ttl: 60_000 })
    clearApiCache('/x')
    await cachedGet('/x', undefined, { ttl: 60_000 })
    expect(get).toHaveBeenCalledTimes(2)
  })

  it('force 选项强制刷新', async () => {
    const get = vi.spyOn(client, 'get').mockResolvedValue([{ id: 1 }])
    await cachedGet('/f', undefined, { ttl: 60_000 })
    await cachedGet('/f', undefined, { ttl: 60_000, force: true })
    expect(get).toHaveBeenCalledTimes(2)
  })

  it('Batch 176：传 signal 命中缓存不重复请求（静态数据跨页共享）', async () => {
    const get = vi.spyOn(client, 'get').mockResolvedValue([{ id: 1 }])
    const ctrl = new AbortController()
    const a = await cachedGet('/sig', undefined, { ttl: 60_000 })
    const b = await cachedGet('/sig', undefined, { ttl: 60_000, signal: ctrl.signal })
    expect(a).toEqual([{ id: 1 }])
    expect(b).toEqual([{ id: 1 }])
    expect(get).toHaveBeenCalledTimes(1)  // 缓存命中，signal 不再绕过缓存
  })

  it('Batch 176：缓存未命中时 signal 请求独立发出并回写缓存', async () => {
    const get = vi.spyOn(client, 'get').mockResolvedValue([{ id: 2 }])
    const ctrl = new AbortController()
    const a = await cachedGet('/sig-miss', undefined, { ttl: 60_000, signal: ctrl.signal })
    expect(a).toEqual([{ id: 2 }])
    expect(get).toHaveBeenCalledTimes(1)
    expect(get).toHaveBeenCalledWith('/sig-miss', { params: undefined, signal: ctrl.signal })

    // 回写缓存后，无 signal 的后续调用不再请求
    const b = await cachedGet('/sig-miss', undefined, { ttl: 60_000 })
    expect(b).toEqual([{ id: 2 }])
    expect(get).toHaveBeenCalledTimes(1)
  })

  it('Batch 176：signal 中止的请求不写入缓存（可取消语义保留）', async () => {
    let rejectFn: ((e: unknown) => void) | undefined
    const get = vi.spyOn(client, 'get').mockImplementation(
      () => new Promise((_resolve, reject) => { rejectFn = reject }) as any,
    )
    const ctrl = new AbortController()
    const p = cachedGet('/sig-abort', undefined, { ttl: 60_000, signal: ctrl.signal })
    ctrl.abort()
    rejectFn!(new Error('canceled'))
    await expect(p).rejects.toThrow('canceled')
    expect(get).toHaveBeenCalledTimes(1)

    // 缓存未被 aborted 结果污染：后续请求仍会发出
    get.mockClear().mockResolvedValue([{ id: 3 }])
    const c2 = await cachedGet('/sig-abort', undefined, { ttl: 60_000 })
    expect(c2).toEqual([{ id: 3 }])
    expect(get).toHaveBeenCalledTimes(1)
  })
})
