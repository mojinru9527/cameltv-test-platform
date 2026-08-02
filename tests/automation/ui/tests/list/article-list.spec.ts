import { expect, test } from '../../utils/ai-test'
import { login } from '../../utils/auth'
import { observeSuccessfulApi, requireStringTestData } from '../../utils/business-oracle'
import { loadTestData } from '../../utils/test-data'
import {
  attachTrafficCapture,
  flushTrafficCapture,
  initTrafficCapture,
} from '../../utils/traffic-capture'

test.describe('LIST - articles', () => {
  let route = ''
  let apiPattern = ''
  let category = ''
  let freeArticle = ''
  let pinnedArticle = ''
  let articleCardSelector = ''
  let detailArticle = ''
  let detailApiPattern = ''

  test.beforeAll(() => {
    const data = loadTestData()
    route = requireStringTestData(data, 'routes.list')
    apiPattern = requireStringTestData(data, 'list.apiPattern')
    category = requireStringTestData(data, 'list.categoryKey')
    freeArticle = requireStringTestData(data, 'list.freeArticleKey')
    pinnedArticle = requireStringTestData(data, 'list.pinnedArticleKey')
    articleCardSelector = requireStringTestData(data, 'list.articleCardSelector')
    detailArticle = requireStringTestData(data, 'list.detailArticleKey')
    detailApiPattern = requireStringTestData(data, 'list.detailApiPattern')
    initTrafficCapture('article-list')
  })
  test.beforeEach(async ({ page }) => {
    attachTrafficCapture(page)
    await login(page)
  })
  test.afterAll(async () => flushTrafficCapture())

  test('TC-LIST-001: configured category is visible', async ({ page }) => {
    await observeSuccessfulApi(page, apiPattern, () => page.goto(route))
    await expect(page.getByText(category, { exact: false }).first()).toBeVisible()
  })

  test('TC-LIST-004: configured free/on-sale article is visible', async ({ page }) => {
    await observeSuccessfulApi(page, apiPattern, () => page.goto(route))
    await expect(page.getByText(freeArticle, { exact: false }).first()).toBeVisible()
  })

  test('TC-LIST-005: configured pinned article is first', async ({ page }) => {
    await observeSuccessfulApi(page, apiPattern, () => page.goto(route))
    await expect(page.locator(articleCardSelector).first()).toContainText(pinnedArticle)
  })

  test('TC-LIST-010: configured article opens a detail API response', async ({ page }) => {
    await observeSuccessfulApi(page, apiPattern, () => page.goto(route))
    const response = await observeSuccessfulApi(page, detailApiPattern, () =>
      page.getByText(detailArticle, { exact: false }).first().click(),
    )
    expect(response.ok()).toBe(true)
    await expect(page.getByText(detailArticle, { exact: false }).first()).toBeVisible()
  })
})
