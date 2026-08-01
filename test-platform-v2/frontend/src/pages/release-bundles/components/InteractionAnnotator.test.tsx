import { describe, expect, it } from 'vitest'
import { parseSavedRegions } from './InteractionAnnotator'

describe('交互标注历史回显', () => {
  it('保留已有坐标并为旧语义标注生成可编辑区域', () => {
    const regions = parseSavedRegions(JSON.stringify([
      {
        trigger: '点击赛事入口',
        target_page: '赛事详情',
        interaction_type: 'navigation',
        x: 12,
        y: 18,
        width: 220,
        height: 64,
      },
      {
        trigger: '点击首页',
        target_page: '首页',
        interaction_type: 'global_navigation',
      },
    ]))

    expect(regions).toHaveLength(2)
    expect(regions[0]).toMatchObject({
      x: 12,
      y: 18,
      width: 220,
      height: 64,
      targetPage: '赛事详情',
    })
    expect(regions[1]).toMatchObject({
      targetPage: '首页',
      isGlobalNav: true,
      width: 140,
      height: 56,
    })
  })

  it('坏 JSON 或非数组输入返回空列表', () => {
    expect(parseSavedRegions('{bad-json')).toEqual([])
    expect(parseSavedRegions(JSON.stringify({ trigger: 'not-an-array' }))).toEqual([])
  })
})
