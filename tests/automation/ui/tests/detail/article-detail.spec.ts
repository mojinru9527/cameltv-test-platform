import { expect, test } from '../../utils/ai-test'
import { login } from '../../utils/auth'
import { observeSuccessfulApi, requireStringTestData } from '../../utils/business-oracle'
import {
  assertRequestMethodAllowed,
  parseRuntimePreconditions,
} from '../../utils/preconditions'
import { loadTestData } from '../../utils/test-data'
import {
  attachTrafficCapture,
  flushTrafficCapture,
  initTrafficCapture,
} from '../../utils/traffic-capture'

test.describe('DETAIL - read-only entitlement', () => {
  let lockedRoute = ''
  let unlockedRoute = ''
  let apiPattern = ''
  let lockedText = ''
  let unlockedText = ''

  test.beforeAll(() => {
    const data = loadTestData()
    lockedRoute = requireStringTestData(data, 'routes.lockedDetail')
    unlockedRoute = requireStringTestData(data, 'routes.unlockedDetail')
    apiPattern = requireStringTestData(data, 'detail.apiPattern')
    lockedText = requireStringTestData(data, 'detail.lockedPredictionText')
    unlockedText = requireStringTestData(data, 'detail.unlockedPredictionText')
    initTrafficCapture('article-detail-readonly')
  })
  test.beforeEach(async ({ page }) => {
    attachTrafficCapture(page)
    await login(page)
  })
  test.afterAll(async () => flushTrafficCapture())

  test('TC-DETAIL-019/020: locked and unlocked records expose distinct configured states', async ({ page }) => {
    await observeSuccessfulApi(page, apiPattern, () => page.goto(lockedRoute))
    await expect(page.getByText(lockedText, { exact: false }).first()).toBeVisible()

    await observeSuccessfulApi(page, apiPattern, () => page.goto(unlockedRoute))
    await expect(page.getByText(unlockedText, { exact: false }).first()).toBeVisible()
  })
})

test.describe('DETAIL - explicitly authorized writes', () => {
  let followRoute = ''
  let lowBalanceRoute = ''
  let followApiPattern = ''
  let unlockApiPattern = ''
  let followButtonText = ''
  let followingText = ''
  let unlockButtonText = ''
  let confirmButtonText = ''
  let insufficientBalanceText = ''

  test.beforeAll(() => {
    const runtime = parseRuntimePreconditions()
    assertRequestMethodAllowed(runtime, 'POST')
    const data = loadTestData()
    followRoute = requireStringTestData(data, 'routes.followDetail')
    lowBalanceRoute = requireStringTestData(data, 'routes.lowBalanceDetail')
    followApiPattern = requireStringTestData(data, 'detail.followApiPattern')
    unlockApiPattern = requireStringTestData(data, 'detail.unlockApiPattern')
    followButtonText = requireStringTestData(data, 'detail.followButtonText')
    followingText = requireStringTestData(data, 'detail.followingText')
    unlockButtonText = requireStringTestData(data, 'detail.unlockButtonText')
    confirmButtonText = requireStringTestData(data, 'detail.confirmButtonText')
    insufficientBalanceText = requireStringTestData(data, 'detail.insufficientBalanceText')
    initTrafficCapture('article-detail-write')
  })
  test.beforeEach(async ({ page }) => {
    attachTrafficCapture(page)
    await login(page)
  })
  test.afterAll(async () => flushTrafficCapture())

  test('TC-DETAIL-005/006: follow action has an API and visible state oracle', async ({ page }) => {
    await page.goto(followRoute)
    await observeSuccessfulApi(page, followApiPattern, () =>
      page.getByText(followButtonText, { exact: true }).click(),
    )
    await expect(page.getByText(followingText, { exact: false }).first()).toBeVisible()
  })

  test('TC-DETAIL-032: low-balance unlock is rejected visibly', async ({ page }) => {
    await page.goto(lowBalanceRoute)
    const response = await observeSuccessfulApi(page, unlockApiPattern, async () => {
      await page.getByText(unlockButtonText, { exact: false }).first().click()
      await page.getByText(confirmButtonText, { exact: false }).first().click()
    })
    expect(response.ok()).toBe(true)
    await expect(
      page.getByText(insufficientBalanceText, { exact: false }).first(),
    ).toBeVisible()
  })
})
