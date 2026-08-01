import { expect, test } from '../../utils/ai-test'
import { login } from '../../utils/auth'
import { observeSuccessfulApi, requireStringTestData } from '../../utils/business-oracle'
import { loadTestData } from '../../utils/test-data'
import {
  attachTrafficCapture,
  flushTrafficCapture,
  initTrafficCapture,
} from '../../utils/traffic-capture'

test.describe('HOME - recommendations', () => {
  let route = ''
  let apiPattern = ''
  let recommendedAuthor = ''
  let expectedYield = ''

  test.beforeAll(() => {
    const data = loadTestData()
    route = requireStringTestData(data, 'routes.home')
    apiPattern = requireStringTestData(data, 'home.apiPattern')
    recommendedAuthor = requireStringTestData(data, 'home.recommendedAuthorKey')
    expectedYield = requireStringTestData(data, 'home.expectedYieldText')
    initTrafficCapture('home-recommend')
  })
  test.beforeEach(async ({ page }) => {
    attachTrafficCapture(page)
    await login(page)
  })
  test.afterAll(async () => flushTrafficCapture())

  test('TC-HOME-001: configured top-Yield author is visible', async ({ page }) => {
    const response = await observeSuccessfulApi(page, apiPattern, () => page.goto(route))
    expect(response.ok()).toBe(true)
    await expect(page.getByText(recommendedAuthor, { exact: false }).first()).toBeVisible()
  })

  test('TC-HOME-002: configured Yield value is visible', async ({ page }) => {
    const response = await observeSuccessfulApi(page, apiPattern, () => page.goto(route))
    expect(response.ok()).toBe(true)
    await expect(page.getByText(expectedYield, { exact: false }).first()).toBeVisible()
  })
})
