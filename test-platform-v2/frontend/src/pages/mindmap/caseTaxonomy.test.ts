import { describe, expect, it } from 'vitest'

import { buildCaseMindmapMarkdown, classifyCaseSurface } from './caseTaxonomy'

describe('用例脑图分类', () => {
  it('识别用户端、运营后台和接口测试', () => {
    expect(classifyCaseSurface('体育-用户端-功能', 'manual')).toBe('用户端')
    expect(classifyCaseSurface('体育-运营后台-功能', 'functional')).toBe('运营后台')
    expect(classifyCaseSurface('体育', 'api')).toBe('接口测试')
  })

  it('按界面、业务域和多级子模块生成脑图', () => {
    const markdown = buildCaseMindmapMarkdown([
      {
        domain: '体育-用户端-功能',
        module: '赛事详情/预测Pick/入口',
        case_type: 'manual',
        priority: 'P0',
        title: '打开预测入口',
      },
      {
        domain: '体育-运营后台-功能',
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
})
