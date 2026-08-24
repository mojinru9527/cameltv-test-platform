import { describe, expect, it } from 'vitest'

import { buildSampleBody, defaultAssertions, sampleValueForProp } from './utils'

describe('A组·样本值优先级（example → default → enum[0]）', () => {
  it('example 优先于 default/enum', () => {
    expect(sampleValueForProp({ type: 'string', example: 'real-20260615', default: 'def', enum: ['a'] })).toBe('real-20260615')
  })

  it('无 example 时取 default', () => {
    expect(sampleValueForProp({ type: 'string', default: 'desc', enum: ['desc', 'asc'] })).toBe('desc')
  })

  it('无 example/default 时取 enum[0]', () => {
    expect(sampleValueForProp({ type: 'string', enum: ['desc', 'asc'] })).toBe('desc')
  })

  it('example 为 0/false/空串时仍然尊重真实值', () => {
    expect(sampleValueForProp({ type: 'integer', example: 0 })).toBe(0)
    expect(sampleValueForProp({ type: 'boolean', example: false })).toBe(false)
    expect(sampleValueForProp({ type: 'string', example: '' })).toBe('')
  })

  it('无契约值时按类型兜底，不再默认占位假数据', () => {
    expect(sampleValueForProp({ type: 'string' }, 'day')).toBe('test_day')
    expect(sampleValueForProp({ type: 'integer', minimum: 1 })).toBe(1)
    expect(sampleValueForProp({ type: 'array' })).toEqual([])
  })
})

describe('A组·buildSampleBody 使用真实值', () => {
  it('按属性生成请求体并保留 example 值', () => {
    const body = buildSampleBody({
      formKey: { type: 'string', example: 'sport_live_follow_conf' },
      day: { type: 'string', example: '20260615' },
      id: { type: 'integer', example: 34779 },
    })
    expect(JSON.parse(body)).toEqual({
      formKey: 'sport_live_follow_conf',
      day: '20260615',
      id: 34779,
    })
  })
})

describe('A组·默认断言非空', () => {
  it('defaultAssertions 至少包含状态码断言（快速调试不再必失败）', () => {
    const rules = JSON.parse(defaultAssertions())
    expect(rules.length).toBeGreaterThan(0)
    expect(rules.some((r: any) => r.type === 'status_code')).toBe(true)
  })
})
