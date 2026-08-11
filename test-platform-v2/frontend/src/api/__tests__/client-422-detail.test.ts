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
