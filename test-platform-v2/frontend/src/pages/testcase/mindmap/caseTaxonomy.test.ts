import { describe, expect, it } from 'vitest'

import { availableCaseSurfaces, buildCaseMindmapMarkdown, caseSurfaceOf } from './caseTaxonomy'

describe('用例脑图分类', () => {
  it('消费后端 surface，不在前端重复推断旧域规则', () => {
    expect(caseSurfaceOf({ domain: '财务管理', surface: '运营后台' })).toBe('运营后台')
    expect(caseSurfaceOf({ domain: '个人中心', surface: '用户端' })).toBe('用户端')
    expect(caseSurfaceOf({ domain: '未来域' })).toBe('其他')
  })

  it('按界面、业务域和多级子模块生成脑图', () => {
    const markdown = buildCaseMindmapMarkdown([
      {
        domain: '体育-用户端-功能',
        surface: '用户端',
        module: '赛事详情/预测Pick/入口',
        case_type: 'manual',
        priority: 'P0',
        title: '打开预测入口',
      },
      {
        domain: '体育-运营后台-功能',
        surface: '运营后台',
        module: '预测管理/玩法配置',
        case_type: 'manual',
        priority: 'P1',
        title: '配置预测玩法',
      },
    ])

    expect(markdown).toContain('## 用户端')
    expect(markdown).toContain('### 体育-用户端-功能')
    expect(markdown).toContain('#### 赛事详情')
    expect(markdown).toContain('##### 预测Pick')
    expect(markdown).toContain('###### 入口')
    expect(markdown).toContain('## 运营后台')
  })

  it('界面筛选只显示实际存在的分类', () => {
    const classified = [
      { surface: '运营后台' },
      { surface: '用户端' },
      { surface: '用户端' },
    ]

    expect(availableCaseSurfaces(classified)).toEqual(['用户端', '运营后台'])
    expect(availableCaseSurfaces([...classified, { surface: '其他' }])).toEqual([
      '用户端',
      '运营后台',
      '其他',
    ])
  })
})
