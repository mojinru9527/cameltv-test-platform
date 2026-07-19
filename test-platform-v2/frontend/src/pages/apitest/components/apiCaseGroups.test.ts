import { describe, expect, it } from 'vitest'

import { groupApiCases } from './apiCaseGroups'

describe('接口用例分组', () => {
  it('优先按稳定接口引用聚合同一接口生成的所有用例', () => {
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
    expect(groups[0].name).toBe('接口C')
    expect(groups[0].endpoint).toBe('/api/c')
    expect(groups[0].cases.map((item) => item.id)).toEqual([1, 2])
  })

  it('旧用例没有接口引用时按方法和去除 Query 的路径分组', () => {
    const groups = groupApiCases([
      { id: 4, api_method: 'GET', api_endpoint: '/api/search?q=one', title: '搜索-one' },
      { id: 5, api_method: 'GET', api_endpoint: '/api/search?q=two', title: '搜索-two' },
    ])

    expect(groups).toHaveLength(1)
    expect(groups[0].key).toBe('GET:/api/search')
    expect(groups[0].cases).toHaveLength(2)
  })
})
