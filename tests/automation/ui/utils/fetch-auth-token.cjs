/**
 * 现场登录业务平台并输出 {userId, userSig} 鉴权 JSON（v1 平台 auth_token 格式）。
 *
 * 用法（测试5 示例）：
 *   $env:CAMELTV_USERNAME='<账号>'; $env:CAMELTV_PASSWORD='<密码>'
 *   $env:CAMELTV_BASE_URL='https://camelive-g3-test5.elelive.cn/'
 *   node utils/fetch-auth-token.cjs
 *
 * 输出：{userId,userSig,...} 的 JSON 字符串（原样作为 Authorization: Bearer 值）。
 * 凭据只从进程环境读取，不写入任何日志/文件；失败时退出码非 0。
 */
const { chromium } = require('@playwright/test')

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

function getCredentials() {
  const username = process.env.CAMELTV_USERNAME?.trim() ?? ''
  const password = process.env.CAMELTV_PASSWORD ?? ''
  if (!username || !password) {
    throw new Error(
      `[auth] missing credentials: CAMELTV_USERNAME${username ? '' : ' (empty)'} CAMELTV_PASSWORD${password ? '' : ' (empty)'}`,
    )
  }
  return { username, password }
}

async function main() {
  const creds = getCredentials()
  const base = (process.env.CAMELTV_BASE_URL?.trim() || 'https://camelive-g3-test5.elelive.cn/').replace(/\/+$/, '')

  const browser = await chromium.launch({ headless: true })
  try {
    const page = await browser.newPage()
    await page.goto(`${base}/login`, { waitUntil: 'domcontentloaded' })

    const usernameInput = page.locator(USERNAME_SELECTOR).first()
    const passwordInput = page.locator(PASSWORD_SELECTOR).first()
    await usernameInput.waitFor({ state: 'visible', timeout: 15_000 })
    await passwordInput.waitFor({ state: 'visible', timeout: 15_000 })
    await usernameInput.fill(creds.username)
    await passwordInput.fill(creds.password)
    await page.locator(SUBMIT_SELECTOR).first().click()

    // 等待登录态写入 localStorage（userId + userSig）
    await page
      .waitForFunction(() => {
        for (let i = 0; i < localStorage.length; i += 1) {
          const value = localStorage.getItem(localStorage.key(i) || '') || ''
          if (value.includes('userSig')) return true
        }
        return false
      }, undefined, { timeout: 20_000 })
      .catch(() => {})

    const token = await page.evaluate(() => {
      for (let i = 0; i < localStorage.length; i += 1) {
        const key = localStorage.key(i) || ''
        const value = localStorage.getItem(key) || ''
        try {
          const parsed = JSON.parse(value)
          if (parsed && parsed.userId && parsed.userSig) {
            return JSON.stringify(parsed)
          }
        } catch {
          // 非 JSON 条目跳过
        }
      }
      return ''
    })

    if (!token) {
      throw new Error('[auth] token not found in localStorage after login (userSig key)')
    }
    process.stdout.write(`${token}\n`)
  } finally {
    await browser.close()
  }
}

main().catch((error) => {
  process.stderr.write(`${error instanceof Error ? error.message : String(error)}\n`)
  process.exit(1)
})
