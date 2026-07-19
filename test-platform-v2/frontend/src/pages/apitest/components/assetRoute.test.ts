import { describe, expect, it } from 'vitest'

import { composeAssetUrl, displayAssetSegment, splitAssetRoute } from './assetRoute'

describe('接口资产路径处理', () => {
  it('按服务、模块和路径拆分示例接口', () => {
    expect(splitAssetRoute('camel-service', '', '/ee/search/synonyms/cou')).toEqual({
      modulePath: '/ee/search',
      endpointPath: '/synonyms/cou',
    })
  })

  it('已有模块路径时保持模块和接口路径不变', () => {
    expect(splitAssetRoute('camel-service', '/ee/search', '/synonyms/cou')).toEqual({
      modulePath: '/ee/search',
      endpointPath: '/synonyms/cou',
    })
  })

  it('拼接环境、服务、模块和路径且不产生重复斜杠', () => {
    expect(composeAssetUrl(
      'http://camel-api-gateway05.svc.elelive.cn/',
      'camel-service',
      '/ee/search',
      '/synonyms/cou',
    )).toBe('http://camel-api-gateway05.svc.elelive.cn/camel-service/ee/search/synonyms/cou')
  })

  it('外显名称用连字符替换斜杠', () => {
    expect(displayAssetSegment('/ee/search')).toBe('ee-search')
    expect(displayAssetSegment('/synonyms/cou')).toBe('synonyms-cou')
  })
})
