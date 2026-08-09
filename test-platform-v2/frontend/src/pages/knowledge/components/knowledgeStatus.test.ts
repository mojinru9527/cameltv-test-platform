import { describe, expect, it } from 'vitest'

import { reviewStatusLabel, sourceStatusLabel } from './knowledgeStatus'

describe('knowledge status labels', () => {
  it.each([
    ['pending', '待审核'],
    ['approved', '已采纳'],
    ['rejected', '已驳回'],
    ['imported', '已导入'],
    ['draft', '草稿'],
  ])('localizes review status %s', (status, label) => {
    expect(reviewStatusLabel(status)).toBe(label)
  })

  it.each([
    ['active', '生效中'],
    ['parsed', '已解析'],
    ['pending', '待处理'],
    ['deprecated', '已废弃'],
    ['superseded', '已替代'],
  ])('localizes source status %s', (status, label) => {
    expect(sourceStatusLabel(status)).toBe(label)
  })

  it('keeps an explicit neutral fallback for unknown values', () => {
    expect(reviewStatusLabel('mystery')).toBe('未知状态（mystery）')
    expect(sourceStatusLabel('')).toBe('未知状态')
  })
})
