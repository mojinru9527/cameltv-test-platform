import { describe, expect, it } from 'vitest'
import { parseSavedRegions, serializeRegions } from './InteractionAnnotator'

describe('交互标注历史回显', () => {
  it('保留已有坐标并为旧语义标注生成可编辑区域', () => {
    const { regions, error } = parseSavedRegions(JSON.stringify([
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

    expect(error).toBe('')
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
      coordinateStatus: 'missing',
      width: 0,
      height: 0,
    })
  })

  it('坏 JSON 或非数组输入返回受控迁移错误', () => {
    expect(parseSavedRegions('{bad-json')).toMatchObject({ regions: [], error: expect.stringContaining('JSON') })
    expect(parseSavedRegions(JSON.stringify({ trigger: 'not-an-array' }))).toMatchObject({
      regions: [],
      error: expect.stringContaining('数组'),
    })
  })

  it('保存时保留真实坐标并拒绝伪造的旧坐标', () => {
    const parsed = parseSavedRegions(JSON.stringify([{
      id: 'saved-region-61',
      trigger: '点击赛事入口',
      target_page: '赛事详情',
      interaction_type: 'navigation',
      x: 12,
      y: 18,
      width: 220,
      height: 64,
    }]))

    expect(serializeRegions(parsed.regions)).toEqual([expect.objectContaining({
      id: 'saved-region-61',
      x: 12,
      y: 18,
      width: 220,
      height: 64,
    })])

    const legacy = parseSavedRegions(JSON.stringify([{
      trigger: '点击首页',
      target_page: '首页',
      interaction_type: 'global_navigation',
    }]))
    expect(() => serializeRegions(legacy.regions)).toThrow('缺少真实坐标')
  })
})
