/**
 * 广告专项观察 fixture — 用于广告行为验证（不拦截广告域）。
 *
 * 与默认 Ad Guard 不同，本 fixture 关闭请求拦截，真实观察广告行为，
 * 但保留「popup 关闭 + 主框架返回」的兜底恢复，并收集 AdEvent 供断言：
 *  - 验证广告弹窗确实出现（广告已投放）
 *  - 验证弹窗可被关闭 / 主框架可返回，且主流程（page 可继续操作）不受影响
 *  - 对应测试需求：「广告跳出去广告页，也要返回来继续探索」
 *
 * 用法：
 *   import { expect } from '../../utils/ai-test'
 *   import { adObservationTest as test } from '../../utils/ad-observe'
 *   test('...', async ({ page, adEvents }) => { ... })
 */
import type { Page } from '@playwright/test'

import { test as base } from './ai-test'
import { installAdGuard, type AdEvent } from './ad-guard'

export interface AdObservationFixtures {
  adEvents: AdEvent[]
}

export const adObservationTest = base.extend<AdObservationFixtures>({
  adEvents: async ({ page }: { page: Page }, use) => {
    const events: AdEvent[] = []
    // 观察模式：不拦截请求（真实观察弹窗），但保留关闭/返回兜底
    const dispose = installAdGuard(page, {
      blockRequests: false,
      closePopups: true,
      recoverMainFrame: true,
      onAdEvent: (e) => events.push(e),
    })
    try {
      await use(events)
    } finally {
      dispose()
    }
  },
})
