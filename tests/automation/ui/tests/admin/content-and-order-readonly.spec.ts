import { expect, test } from '../../utils/ai-test'
import { login } from '../../utils/auth'
import { observeSuccessfulApi, requireStringTestData } from '../../utils/business-oracle'
import { loadTestData } from '../../utils/test-data'
import {
  attachTrafficCapture,
  flushTrafficCapture,
  initTrafficCapture,
} from '../../utils/traffic-capture'

test.describe('ADMIN - content and order read-only reconciliation', () => {
  let contentRoute = ''
  let orderRoute = ''
  let contentApiPattern = ''
  let orderApiPattern = ''
  let contentRecord = ''
  let orderRecord = ''

  test.beforeAll(() => {
    const data = loadTestData()
    contentRoute = requireStringTestData(data, 'routes.adminContent')
    orderRoute = requireStringTestData(data, 'routes.adminOrder')
    contentApiPattern = requireStringTestData(data, 'admin.contentApiPattern')
    orderApiPattern = requireStringTestData(data, 'admin.orderApiPattern')
    contentRecord = requireStringTestData(data, 'admin.contentRecordText')
    orderRecord = requireStringTestData(data, 'admin.orderRecordText')
    initTrafficCapture('admin-readonly')
  })
  test.beforeEach(async ({ page }) => {
    attachTrafficCapture(page)
    await login(page)
  })
  test.afterAll(async () => flushTrafficCapture())

  test('TC-ADMIN-001: configured content record is observable', async ({ page }) => {
    const response = await observeSuccessfulApi(page, contentApiPattern, () =>
      page.goto(contentRoute),
    )
    expect(response.ok()).toBe(true)
    await expect(page.getByText(contentRecord, { exact: false }).first()).toBeVisible()
  })

  test('TC-ADMIN-002: configured order record is observable', async ({ page }) => {
    const response = await observeSuccessfulApi(page, orderApiPattern, () =>
      page.goto(orderRoute),
    )
    expect(response.ok()).toBe(true)
    await expect(page.getByText(orderRecord, { exact: false }).first()).toBeVisible()
  })
})
