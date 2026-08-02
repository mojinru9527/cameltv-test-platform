/**
 * Deterministic login helpers for CamelTv browser tests.
 *
 * Credentials are read only from the local process environment and are filled
 * directly through Playwright locators. They must never be included in an AI
 * prompt, log message, screenshot name, or persisted traffic capture.
 */
import type { Page } from '@playwright/test'
import {
  BlockedRunError,
  assertNetworkRequestAllowed,
  parseRuntimePreconditions,
} from './preconditions'

export interface LoginCredentials {
  username: string
  password: string
}

type LoginEnvironment = Record<string, string | undefined>

const USERNAME_SELECTOR = [
  'input[name="username"]',
  'input[name="email"]',
  'input[name="phone"]',
  'input[type="email"]',
  'input[type="tel"]',
  'input[autocomplete="username"]',
  'input[type="text"]',
].join(', ')

const PASSWORD_SELECTOR = [
  'input[name="password"]',
  'input[type="password"]',
  'input[autocomplete="current-password"]',
].join(', ')

const SUBMIT_SELECTOR = [
  'button[type="submit"]',
  '[data-testid="login-submit"]',
  'button:has-text("登录")',
  'button:has-text("Sign In")',
].join(', ')

const USER_MENU_SELECTOR = [
  '[data-testid="user-menu"]',
  '[data-testid="profile-menu"]',
  'button[aria-label*="user" i]',
  'button[aria-label*="profile" i]',
  'button:has-text("退出")',
  'button:has-text("Logout")',
].join(', ')

const LOGIN_ENTRY_SELECTOR = [
  '[data-testid="login-btn"]',
  'a[href*="login"]',
  'button:has-text("登录")',
  'button:has-text("Sign In")',
].join(', ')

const LOGIN_ERROR_SELECTOR = [
  '[role="alert"]',
  '.toast-error',
  '[data-testid="login-error"]',
].join(', ')

/** Return configured credentials or fail before any browser interaction. */
export function getLoginCredentials(
  environment: LoginEnvironment = process.env,
): LoginCredentials {
  const username = environment.CAMELTV_USERNAME?.trim() ?? ''
  const password = environment.CAMELTV_PASSWORD ?? ''
  const missing: string[] = []
  if (!username) missing.push('CAMELTV_USERNAME')
  if (!password) missing.push('CAMELTV_PASSWORD')
  if (missing.length > 0) {
    throw new BlockedRunError(
      missing.join(','),
      environment.CAMELTV_ACCOUNT_OWNER?.trim() || 'UNASSIGNED',
      'required login credentials are missing',
    )
  }
  return { username, password }
}

/** Fill and submit the login form without exposing credentials to AI helpers. */
export async function fillLoginForm(
  page: Page,
  credentials: LoginCredentials,
): Promise<void> {
  const usernameInput = page.locator(USERNAME_SELECTOR).first()
  const passwordInput = page.locator(PASSWORD_SELECTOR).first()
  const submitButton = page.locator(SUBMIT_SELECTOR).first()

  await usernameInput.waitFor({ state: 'visible', timeout: 10_000 })
  await passwordInput.waitFor({ state: 'visible', timeout: 10_000 })
  await usernameInput.fill(credentials.username)
  await passwordInput.fill(credentials.password)
  await submitButton.waitFor({ state: 'visible', timeout: 10_000 })
  await submitButton.click()
}

/** Log in and require an observable authenticated user-menu marker. */
export async function login(page: Page): Promise<void> {
  const credentials = getLoginCredentials()
  const runtime = parseRuntimePreconditions()
  await page.route('**/*', async (route) => {
    const request = route.request()
    try {
      assertNetworkRequestAllowed(runtime, request.url(), request.method())
    } catch (error) {
      await route.abort('blockedbyclient')
      throw error
    }
    await route.continue()
  })
  await page.goto('/', { waitUntil: 'domcontentloaded' })

  const userMenu = page.locator(USER_MENU_SELECTOR).first()
  if (await userMenu.isVisible().catch(() => false)) return

  const loginEntry = page.locator(LOGIN_ENTRY_SELECTOR).first()
  if (await loginEntry.isVisible().catch(() => false)) {
    await loginEntry.click()
  } else {
    await page.goto('/login', { waitUntil: 'domcontentloaded' })
  }

  await fillLoginForm(page, credentials)

  try {
    await userMenu.waitFor({ state: 'visible', timeout: 15_000 })
  } catch {
    const errorLocator = page.locator(LOGIN_ERROR_SELECTOR).first()
    const errorText = await errorLocator.isVisible().catch(() => false)
      ? (await errorLocator.textContent())?.trim()
      : ''
    throw new Error(
      errorText
        ? `[auth] Login failed: ${errorText}`
        : '[auth] Login failed: authenticated user menu did not appear',
    )
  }
}

/** Log out through deterministic menu locators. */
export async function logout(page: Page): Promise<void> {
  const userMenu = page.locator(USER_MENU_SELECTOR).first()
  await userMenu.waitFor({ state: 'visible', timeout: 10_000 })
  await userMenu.click()

  const logoutAction = page
    .locator('button:has-text("退出"), button:has-text("Logout"), [data-testid="logout"]')
    .first()
  await logoutAction.waitFor({ state: 'visible', timeout: 5_000 })
  await logoutAction.click()
  await page.locator(PASSWORD_SELECTOR).first().waitFor({ state: 'visible', timeout: 10_000 })
}
