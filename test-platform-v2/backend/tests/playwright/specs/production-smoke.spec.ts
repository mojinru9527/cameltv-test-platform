import { expect, test, type Page } from '@playwright/test'

import {
  assertApiAssetsObserved,
  assertAuthenticatedSession,
  assertProductionRequestAllowed,
  readAuthorizedLogin,
  readProductionSmokeRuntime,
  type ApiAssetObservation,
  type AuthorizedLogin,
  type ProductionSmokeRuntime,
} from '../support/production-smoke-contract'

const API_URL_PATTERN = /\/api\/|api\./i
const LOGIN_ERROR_SELECTOR = '[role="alert"], .toast-error, [data-testid="login-error"]'
const USER_MENU_SELECTOR = [
  '[data-testid="user-menu"]',
  '[data-testid="profile-menu"]',
  'button:has-text("Logout")',
  'button:has-text("退出")',
].join(', ')

async function guardProductionRequests(
  page: Page,
  runtime: ProductionSmokeRuntime,
  allowWrite = false,
): Promise<string[]> {
  const rejected: string[] = []
  await page.route('**/*', async (route) => {
    const request = route.request()
    try {
      assertProductionRequestAllowed(
        runtime,
        request.url(),
        request.method(),
        allowWrite,
      )
      await route.continue()
      return
    } catch (error) {
      rejected.push(error instanceof Error ? error.message : String(error))
      await route.abort('blockedbyclient')
    }
  })
  return rejected
}

test.describe('CamelTv production read-only smoke', () => {
  let runtime: ProductionSmokeRuntime

  test.beforeAll(() => {
    runtime = readProductionSmokeRuntime()
  })

  test.beforeEach(async ({ page }) => {
    page.setDefaultTimeout(15_000)
    page.setDefaultNavigationTimeout(20_000)
  })

  test('TC-PROD-001: homepage exposes the expected business fixture', async ({ page }) => {
    const rejected = await guardProductionRequests(page, runtime)
    const response = await page.goto(runtime.baseUrl.toString(), {
      waitUntil: 'domcontentloaded',
    })

    expect(response?.status() ?? 0).toBeGreaterThanOrEqual(200)
    expect(response?.status() ?? 500).toBeLessThan(400)
    await expect(page.getByText(runtime.expectedBusinessText, { exact: false }).first()).toBeVisible()
    expect(rejected).toEqual([])
  })

  test('TC-PROD-003: core page has an observable navigation surface', async ({ page }) => {
    const rejected = await guardProductionRequests(page, runtime)
    await page.goto(runtime.baseUrl.toString(), { waitUntil: 'domcontentloaded' })

    const clickables = page.locator('a[href], button, [role="button"]')
    await expect(clickables.first()).toBeVisible()
    expect(await clickables.count()).toBeGreaterThan(0)
    expect(rejected).toEqual([])
  })

  test('TC-PROD-004: homepage observes at least one successful core API asset', async ({ page }) => {
    const observations: ApiAssetObservation[] = []
    const rejected = await guardProductionRequests(page, runtime)
    page.on('response', (response) => {
      if (API_URL_PATTERN.test(response.url())) {
        observations.push({ url: response.url(), status: response.status() })
      }
    })

    await page.goto(runtime.baseUrl.toString(), { waitUntil: 'networkidle' })

    assertApiAssetsObserved(observations)
    expect(rejected).toEqual([])
  })

  test('TC-PROD-005: homepage load remains inside the 15 second baseline', async ({ page }) => {
    const rejected = await guardProductionRequests(page, runtime)
    const startedAt = Date.now()
    await page.goto(runtime.baseUrl.toString(), { waitUntil: 'load' })

    expect(Date.now() - startedAt).toBeLessThan(15_000)
    expect(rejected).toEqual([])
  })
})

test.describe('CamelTv explicitly authorized production login smoke', () => {
  let runtime: ProductionSmokeRuntime
  let credentials: AuthorizedLogin

  test.beforeAll(() => {
    runtime = readProductionSmokeRuntime()
    credentials = readAuthorizedLogin()
  })

  test('TC-PROD-002: supplied credentials create an observable session', async ({ page }) => {
    const rejected = await guardProductionRequests(page, runtime, true)
    await page.goto(new URL('/login', runtime.baseUrl).toString(), {
      waitUntil: 'domcontentloaded',
    })

    await page
      .locator('input[type="tel"], input[name*="phone"], input[name*="username"], input[type="text"]')
      .first()
      .fill(credentials.username)
    await page.locator('input[type="password"]').first().fill(credentials.password)
    await page
      .locator('button[type="submit"], button:has-text("登录"), button:has-text("Sign In")')
      .first()
      .click()

    const userMenu = page.locator(USER_MENU_SELECTOR).first()
    const error = page.locator(LOGIN_ERROR_SELECTOR).first()
    await Promise.race([
      userMenu.waitFor({ state: 'visible', timeout: 15_000 }),
      error.waitFor({ state: 'visible', timeout: 15_000 }),
    ]).catch(() => undefined)

    const authenticated = await userMenu.isVisible().catch(() => false)
    const errorText = (await error.textContent().catch(() => '')) ?? ''
    assertAuthenticatedSession(authenticated, errorText)
    expect(rejected).toEqual([])
  })
})
