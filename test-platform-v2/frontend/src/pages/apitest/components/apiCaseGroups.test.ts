import { describe, expect, it } from 'vitest'

import { groupApiCases } from './apiCaseGroups'

describe('接口用例分组', () => {
  it('按 api_spec_ref 聚合同一接口生成的所有用例', () => {
    const groups = groupApiCases([
      {
        id: 1,
        api_spec_ref: 'api_endpoint:9',
        api_method: 'POST',
        api_endpoint: '/api/c',
        title: '【正向】接口C - 正常请求',
      },
      {
        id: 2,
        api_spec_ref: 'api_endpoint:9',
        api_method: 'POST',
        api_endpoint: '/api/c?age=bad',
        title: '【类型校验】接口C - age - 类型错误',
      },
      {
        id: 3,
        api_spec_ref: 'api_endpoint:10',
        api_method: 'GET',
        api_endpoint: '/api/d',
        title: '【正向】接口D - 正常请求',
      },
    ])

    expect(groups).toHaveLength(2)
    // Group 0: api_endpoint:9 — displays as the shorter/cleaner endpoint
    expect(groups[0].name).toBe('[POST] /api/c')
    expect(groups[0].method).toBe('POST')
    expect(groups[0].endpoint).toBe('/api/c')
    expect(groups[0].cases.map((item) => item.id)).toEqual([1, 2])

    // Group 1: api_endpoint:10
    expect(groups[1].name).toBe('[GET] /api/d')
    expect(groups[1].cases.map((item) => item.id)).toEqual([3])
  })

  it('旧用例没有 api_spec_ref 时按 method:endpoint 分组', () => {
    const groups = groupApiCases([
      { id: 4, api_method: 'GET', api_endpoint: '/api/search?q=one', title: '搜索-one' },
      { id: 5, api_method: 'GET', api_endpoint: '/api/search?q=two', title: '搜索-two' },
    ])

    expect(groups).toHaveLength(1)
    expect(groups[0].key).toBe('GET:/api/search')
    expect(groups[0].method).toBe('GET')
    expect(groups[0].endpoint).toBe('/api/search')
    expect(groups[0].cases).toHaveLength(2)
  })

  it('不同 method 的相同路径分到不同组', () => {
    const groups = groupApiCases([
      { id: 6, api_method: 'GET', api_endpoint: '/api/items', title: '列表' },
      { id: 7, api_method: 'POST', api_endpoint: '/api/items', title: '创建' },
    ])

    expect(groups).toHaveLength(2)
  })
})
