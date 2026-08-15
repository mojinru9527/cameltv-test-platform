import { expect, test as base } from '@playwright/test'
import {
  PlaywrightAiFixture,
  type PlayWrightAiFixtureType,
} from '@midscene/web/playwright'

import { installAdGuardOnContext } from './ad-guard'

/**
 * 默认测试基座：midscene AI fixture + 全局广告防御（Ad Guard）。
 *
 * Ad Guard 在 context 层安装：每个 page（含 popup）自动拦截线上实测的
 * 广告联盟域请求（andallthemise.org / eflewandatnig.org / ukankingwithea.com
 * / bestfungamestoday.com / moonlighthathel.org / take-look.com），
 * 并兜底关闭 popup、整页广告跳转后返回主站。
 *
 * 广告行为专项验证请使用 `utils/ad-observe.ts` 的 adObservationTest
 * （关闭拦截、真实观察并断言弹窗行为）。
 */
export const test = base.extend<PlayWrightAiFixtureType>({
  ...PlaywrightAiFixture(),
  context: async ({ context }, use) => {
    const dispose = installAdGuardOnContext(context)
    try {
      await use(context)
    } finally {
      dispose()
    }
  },
})
export { expect }
