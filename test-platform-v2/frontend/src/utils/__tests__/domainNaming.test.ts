import { describe, expect, it } from 'vitest'

import {
  DOMAIN_GROUP_ORDER,
  compareDomainGroups,
  groupDomainLabel,
  groupDomains,
} from '../domainNaming'

describe('domainNaming（Batch 182 / FIX-173-P3-04）', () => {
  it('平台前缀直接取前缀并保留原名', () => {
    expect(groupDomainLabel('用户端/首页')).toEqual({ group: '用户端', label: '用户端/首页' })
    expect(groupDomainLabel('运营后台/广告管理')).toEqual({ group: '运营后台', label: '运营后台/广告管理' })
    expect(groupDomainLabel('接口测试/业务接口')).toEqual({ group: '接口测试', label: '接口测试/业务接口' })
  })

  it('平台名本身的裸值归对应组且不改标签', () => {
    expect(groupDomainLabel('接口测试')).toEqual({ group: '接口测试', label: '接口测试' })
    expect(groupDomainLabel('用户端')).toEqual({ group: '用户端', label: '用户端' })
  })

  it('连字符平台前缀与业务-运营后台-* 归运营后台组', () => {
    expect(groupDomainLabel('运营后台-热门比赛配置')).toEqual({
      group: '运营后台',
      label: '运营后台-热门比赛配置',
    })
    expect(groupDomainLabel('业务-运营后台-功能')).toEqual({
      group: '运营后台',
      label: '业务-运营后台-功能',
    })
  })

  it('裸域归用户端组且标签补前缀保留原名', () => {
    expect(groupDomainLabel('UGC')).toEqual({ group: '用户端', label: '用户端/UGC' })
    expect(groupDomainLabel('广告')).toEqual({ group: '用户端', label: '用户端/广告' })
    expect(groupDomainLabel('APP-版本更新')).toEqual({ group: '用户端', label: '用户端/APP-版本更新' })
  })

  it('空值/空白归其他并展示为未分类', () => {
    expect(groupDomainLabel('')).toEqual({ group: '其他', label: '未分类' })
    expect(groupDomainLabel('   ')).toEqual({ group: '其他', label: '未分类' })
    expect(groupDomainLabel(null)).toEqual({ group: '其他', label: '未分类' })
    expect(groupDomainLabel(undefined)).toEqual({ group: '其他', label: '未分类' })
  })

  it('已归一的值不会被二次加前缀（幂等展示）', () => {
    expect(groupDomainLabel('用户端/UGC')).toEqual({ group: '用户端', label: '用户端/UGC' })
    expect(groupDomainLabel('用户端/广告')).toEqual({ group: '用户端', label: '用户端/广告' })
  })

  it('groupDomains 按 DOMAIN_GROUP_ORDER 聚合，组内保持传入顺序', () => {
    const items = [
      { domain: '广告', count: 1 },
      { domain: 'UGC', count: 2 },
      { domain: '接口测试/订单', count: 3 },
      { domain: '运营后台/广告管理', count: 4 },
      { domain: '用户端/首页', count: 5 },
    ]
    expect(groupDomains(items, (i) => i.domain).map(([group]) => group)).toEqual(
      ['用户端', '运营后台', '接口测试'],
    )
    const userGroup = groupDomains(items, (i) => i.domain)[0]
    expect(userGroup[1].map((i) => i.domain)).toEqual(['广告', 'UGC', '用户端/首页'])
    expect(DOMAIN_GROUP_ORDER).toEqual(['用户端', '运营后台', '接口测试', '其他'])
  })

  it('compareDomainGroups 按 DOMAIN_GROUP_ORDER 排序，未知组兜底最后', () => {
    expect(compareDomainGroups('用户端', '运营后台')).toBeLessThan(0)
    expect(compareDomainGroups('接口测试', '用户端')).toBeGreaterThan(0)
    expect(compareDomainGroups('其他', '接口测试')).toBeGreaterThan(0)
    expect(compareDomainGroups('未知组', '其他')).toBeGreaterThan(0)
  })
})
