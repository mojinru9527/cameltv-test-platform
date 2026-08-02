import { expect, test } from '../../utils/ai-test'
import { login } from '../../utils/auth'
import { observeSuccessfulApi, requireStringTestData } from '../../utils/business-oracle'
import { loadTestData } from '../../utils/test-data'
import {
  attachTrafficCapture,
  flushTrafficCapture,
  initTrafficCapture,
} from '../../utils/traffic-capture'

test.describe('BONUS - recharge package labels', () => {
  let route = ''
  let apiPattern = ''
  let bonusPackage = ''
  let nonBonusPackage = ''

  test.beforeAll(() => {
    const data = loadTestData()
    route = requireStringTestData(data, 'routes.recharge')
    apiPattern = requireStringTestData(data, 'bonus.apiPattern')
    bonusPackage = requireStringTestData(data, 'bonus.bonusPackageText')
    nonBonusPackage = requireStringTestData(data, 'bonus.nonBonusPackageText')
    initTrafficCapture('bonus-packages-readonly')
  })
  test.beforeEach(async ({ page }) => {
    attachTrafficCapture(page)
    await login(page)
  })
  test.afterAll(async () => flushTrafficCapture())

  test('TC-BONUS-001: configured bonus package exposes its bonus label', async ({ page }) => {
    await observeSuccessfulApi(page, apiPattern, () => page.goto(route))
    await expect(page.getByText(bonusPackage, { exact: false }).first()).toBeVisible()
  })

  test('TC-BONUS-002: configured non-bonus package remains distinguishable', async ({ page }) => {
    await observeSuccessfulApi(page, apiPattern, () => page.goto(route))
    await expect(page.getByText(nonBonusPackage, { exact: false }).first()).toBeVisible()
  })
})
