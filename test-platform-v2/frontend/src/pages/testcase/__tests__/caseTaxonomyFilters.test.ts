import { describe, expect, it } from 'vitest'

import { buildCaseListParams, flattenTaxonomyModules } from '../caseTaxonomyFilters'

describe('case taxonomy filters', () => {
  it('flattens canonical parent and child module paths without client wrappers', () => {
    const options = flattenTaxonomyModules([{
      name: '预测Pick',
      path: '预测Pick',
      count: 8,
      children: [{
        name: '异常处理',
        path: '预测Pick/异常处理',
        count: 3,
        children: [],
      }],
    }])

    expect(options).toEqual([
      { value: '预测Pick', label: '预测Pick (8)' },
      { value: '预测Pick/异常处理', label: '预测Pick/异常处理 (3)' },
    ])
    expect(JSON.stringify(options)).not.toMatch(/PC-web|安卓iOS|移动端-web/i)
  })

  it('uses normalized API filter names and keeps empty filters out', () => {
    expect(buildCaseListParams({
      surface: '用户端',
      domain: '赛事详情',
      modulePath: '预测Pick',
      nature: 'negative',
    }, { page: 2, page_size: 20, case_type: 'manual' })).toEqual({
      page: 2,
      page_size: 20,
      case_type: 'manual',
      surface: '用户端',
      taxonomy_domain: '赛事详情',
      taxonomy_module: '预测Pick',
      positive_negative: 'negative',
    })
  })
})
