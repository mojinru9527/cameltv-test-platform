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
      'https://api.example.com/',
      'camel-service',
      '/ee/search',
      '/synonyms/cou',
    )).toBe('https://api.example.com/camel-service/ee/search/synonyms/cou')
  })

  it('外显名称用连字符替换斜杠', () => {
    expect(displayAssetSegment('/ee/search')).toBe('ee-search')
    expect(displayAssetSegment('/synonyms/cou')).toBe('synonyms-cou')
  })

  it('A组：tags 当模块且不是路径前缀时，不误作模块路径（从 path 推导）', () => {
    // 证据：module=live-controller（tags[0]），path=/ee/live/home_match
    // 旧实现把 controller 名拼进 URL → …/camel-service/live-controller/ee/live/home_match
    expect(splitAssetRoute('camel-service', 'live-controller', '/ee/live/home_match')).toEqual({
      modulePath: '/ee/live',
      endpointPath: '/home_match',
    })
    expect(composeAssetUrl(
      'https://api.example.com',
      'camel-service',
      '/ee/live',
      '/home_match',
    )).toBe('https://api.example.com/camel-service/ee/live/home_match')
  })

  it('A组：path 已含服务名前缀时不再双拼 serviceName', () => {
    expect(splitAssetRoute('camel-service', '', '/camel-service/ee/live/home_match')).toEqual({
      modulePath: '/ee/live',
      endpointPath: '/home_match',
    })
    expect(composeAssetUrl(
      'https://api.example.com',
      'camel-service',
      '/ee/live',
      '/home_match',
    )).toBe('https://api.example.com/camel-service/ee/live/home_match')
  })

  it('A组：base 已含服务名尾段时不再重复拼接服务名', () => {
    expect(composeAssetUrl(
      'https://api.example.com/camel-service',
      'camel-service',
      '/ee/live',
      '/home_match',
    )).toBe('https://api.example.com/camel-service/ee/live/home_match')
  })
})
