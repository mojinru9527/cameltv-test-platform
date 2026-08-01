import { expect, test } from '../../utils/ai-test'
import { login } from '../../utils/auth'
import { observeSuccessfulApi, requireStringTestData } from '../../utils/business-oracle'
import { loadTestData } from '../../utils/test-data'
import {
  attachTrafficCapture,
  flushTrafficCapture,
  initTrafficCapture,
} from '../../utils/traffic-capture'

test.describe('REFUND - first-bet protection read-only history', () => {
  let route = ''
  let apiPattern = ''
  let eligibleText = ''
  let lossRefundText = ''
  let winNoRefundText = ''
  let usedEligibilityText = ''

  test.beforeAll(() => {
    const data = loadTestData()
    route = requireStringTestData(data, 'routes.refundHistory')
    apiPattern = requireStringTestData(data, 'refund.apiPattern')
    eligibleText = requireStringTestData(data, 'refund.eligibleRecordText')
    lossRefundText = requireStringTestData(data, 'refund.lossRefundRecordText')
    winNoRefundText = requireStringTestData(data, 'refund.winNoRefundRecordText')
    usedEligibilityText = requireStringTestData(data, 'refund.usedEligibilityRecordText')
    initTrafficCapture('refund-history-readonly')
  })
  test.beforeEach(async ({ page }) => {
    attachTrafficCapture(page)
    await login(page)
  })
  test.afterAll(async () => flushTrafficCapture())

  for (const [caseId, expectedText] of [
    ['TC-REFUND-001: eligible account is identified', () => eligibleText],
    ['TC-REFUND-004: settled Loss has a refund record', () => lossRefundText],
    ['TC-REFUND-005: settled Win has no-refund evidence', () => winNoRefundText],
    ['TC-REFUND-007: used eligibility remains consumed', () => usedEligibilityText],
  ] as const) {
    test(caseId, async ({ page }) => {
      await observeSuccessfulApi(page, apiPattern, () => page.goto(route))
      await expect(page.getByText(expectedText(), { exact: false }).first()).toBeVisible()
    })
  }
})
