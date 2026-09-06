import { describe, expect, it } from 'vitest'
import { normalizeApiErrorMessage } from '../errorMessage'

describe('normalizeApiErrorMessage', () => {
  it('formats FastAPI validation arrays as readable text', () => {
    expect(
      normalizeApiErrorMessage(
        {
          detail: [
            { loc: ['body', 'scenario_version_id'], msg: 'Field required' },
            { loc: ['body', 'environment_id'], msg: 'Input should be a valid integer' },
          ],
        },
        'Request failed with status code 422',
      ),
    ).toBe(
      '请求参数校验失败：scenario_version_id: Field required; environment_id: Input should be a valid integer',
    )
  })

  it('extracts a readable message from structured detail objects', () => {
    expect(
      normalizeApiErrorMessage(
        { detail: { code: 'PLAN_MISSING', message: '场景尚未生成执行计划' } },
        'Request failed',
      ),
    ).toBe('场景尚未生成执行计划')
  })

  it('preserves string details', () => {
    expect(normalizeApiErrorMessage({ detail: '执行不存在' }, 'Request failed')).toBe('执行不存在')
  })

  it('falls back to the transport message when no API message exists', () => {
    expect(normalizeApiErrorMessage(undefined, '网络断开')).toBe('网络断开')
  })
})
