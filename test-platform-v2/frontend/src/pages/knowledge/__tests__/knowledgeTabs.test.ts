import { describe, expect, it } from 'vitest'

import { NORMAL_KNOWLEDGE_TABS, NORMAL_TAB_LIMIT } from '../index'

/**
 * Batch 260 / B3-5 — 知识中心只读视图收敛。
 *
 * DoD：普通用户 Tab ≤3。
 * 背景：该文件自己的 docblock 一直写"普通用户只留 3 Tab"，但代码实际放宽到 5 个
 * （`project/platform/versionrecords/reuse/search`）——**代码与自己的注释漂移**。
 * 本测试把"≤3"固化成可执行校验，防止再次回涨。
 */
describe('知识中心普通用户页签', () => {
  it('数量不超过 3', () => {
    expect(NORMAL_KNOWLEDGE_TABS.size).toBeLessThanOrEqual(NORMAL_TAB_LIMIT)
    expect(NORMAL_TAB_LIMIT).toBe(3)
  })

  it('恰好是 影响面 / 项目知识 / 检索 三个', () => {
    expect([...NORMAL_KNOWLEDGE_TABS].sort()).toEqual(['impact', 'project', 'search'])
  })

  it('包含知识主线入口（影响面）', () => {
    expect(NORMAL_KNOWLEDGE_TABS.has('impact')).toBe(true)
  })

  it('不再把版本记录/复用建议作为独立页签占用普通用户额度', () => {
    expect(NORMAL_KNOWLEDGE_TABS.has('versionrecords')).toBe(false)
    expect(NORMAL_KNOWLEDGE_TABS.has('reuse')).toBe(false)
  })
})
