import { describe, expect, it, vi, afterEach } from 'vitest'
import client from '../client'

// 直接取响应拦截器的 rejected 分支做单测（遍历 handlers 定位错误处理函数，避免依赖索引）
const errorHandler = client.interceptors.response.handlers
  .map((h) => (h as { rejected?: unknown })?.rejected)
  .find((fn): fn is (err: any) => Promise<any> => typeof fn === 'function') ?? null

afterEach(() => {
  vi.restoreAllMocks()
})

describe('client 422 detail 规范化', () => {
  it('数组型 detail 被转为可读字符串，避免对象作为 React child 渲染崩溃', async () => {
    expect(errorHandler).toBeTypeOf('function')
    const fakeErr = {
      response: {
        status: 422,
        data: {
          detail: [
            { loc: ['body', 'assignee_id'], msg: 'Input should be a valid integer', type: 'int_type' },
            { loc: ['body', 'title'], msg: 'Field required', type: 'missing' },
          ],
        },
      },
      message: 'Request failed with status code 422',
      config: {},
    }
    await expect(errorHandler!(fakeErr)).rejects.toMatchObject({
      message: '请求参数校验失败：assignee_id: Input should be a valid integer; title: Field required',
    })
  })

  it('字符串 detail 保持透传', async () => {
    const fakeErr = {
      response: { status: 404, data: { detail: '缺陷不存在' } },
      message: 'Request failed with status code 404',
      config: {},
    }
    await expect(errorHandler!(fakeErr)).rejects.toMatchObject({ message: '缺陷不存在' })
  })

  it('无 response 时回退到 err.message', async () => {
    const fakeErr = { message: '网络错误', config: {} }
    await expect(errorHandler!(fakeErr)).rejects.toMatchObject({ message: '网络错误' })
  })
})


const fulfilled = client.interceptors.response.handlers
  .map((h) => (h as { fulfilled?: unknown })?.fulfilled)
  .find((fn): fn is (resp: any) => Promise<any> => typeof fn === 'function') ?? null

describe('client envelope 业务错误携带 code（Batch 160）', () => {
  it('HTTP 200 + code=404 的 envelope 被转为带 code 的错误，供调用方按 code 分支', async () => {
    expect(fulfilled).toBeTypeOf('function')
    const fakeResp = { data: { code: 404, msg: '功能拆分结果', data: null } }
    await expect(fulfilled!(fakeResp)).rejects.toMatchObject({
      message: '功能拆分结果',
      code: 404,
    })
  })

  it('code=0 时正常返回 data', async () => {
    const fakeResp = { data: { code: 0, msg: 'ok', data: { id: 1 } } }
    expect(fulfilled!(fakeResp)).toEqual({ id: 1 })
  })
})
