import { expect, test } from '../../utils/ai-test'
import { login } from '../../utils/auth'
import { observeSuccessfulApi, requireStringTestData } from '../../utils/business-oracle'
import { loadTestData } from '../../utils/test-data'
import {
  attachTrafficCapture,
  flushTrafficCapture,
  initTrafficCapture,
} from '../../utils/traffic-capture'

test.describe('PAY - recharge read-only surface', () => {
  let route = ''
  let apiPattern = ''
  let balanceText = ''
  let fiatTabText = ''
  let packageText = ''
  let proceedButtonText = ''

  test.beforeAll(() => {
    const data = loadTestData()
    route = requireStringTestData(data, 'routes.recharge')
    apiPattern = requireStringTestData(data, 'pay.apiPattern')
    balanceText = requireStringTestData(data, 'pay.expectedBalanceText')
    fiatTabText = requireStringTestData(data, 'pay.fiatTabText')
    packageText = requireStringTestData(data, 'pay.packageKey')
    proceedButtonText = requireStringTestData(data, 'pay.proceedButtonText')
    initTrafficCapture('recharge-readonly')
  })
  test.beforeEach(async ({ page }) => {
    attachTrafficCapture(page)
    await login(page)
  })
  test.afterAll(async () => flushTrafficCapture())

  test('TC-PAY-001: configured balance is visible', async ({ page }) => {
    await observeSuccessfulApi(page, apiPattern, () => page.goto(route))
    await expect(page.getByText(balanceText, { exact: false }).first()).toBeVisible()
  })

  test('TC-PAY-004: fiat tab is selected by default', async ({ page }) => {
    await observeSuccessfulApi(page, apiPattern, () => page.goto(route))
    await expect(page.getByRole('tab', { name: fiatTabText }).first()).toHaveAttribute(
      'aria-selected',
      'true',
    )
  })

  test('TC-PAY-010: configured package is visible', async ({ page }) => {
    await observeSuccessfulApi(page, apiPattern, () => page.goto(route))
    await expect(page.getByText(packageText, { exact: false }).first()).toBeVisible()
  })

  test('TC-PAY-016: order action is visible but not invoked', async ({ page }) => {
    await observeSuccessfulApi(page, apiPattern, () => page.goto(route))
    await expect(
      page.getByRole('button', { name: proceedButtonText }).first(),
    ).toBeVisible()
  })
})
