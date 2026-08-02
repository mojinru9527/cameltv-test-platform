/**
 * 现场登录业务平台并输出 {userId, userSig} 鉴权 JSON（v1 平台 auth_token 格式）。
 *
 * 用法（测试5 示例）：
 *   $env:CAMELTV_USERNAME='<账号>'; $env:CAMELTV_PASSWORD='<密码>'
 *   $env:CAMELTV_BASE_URL='https://camelive-g3-test5.elelive.cn/'
 *   node utils/fetch-auth-token.cjs
 * 账号为手机号时（纯账密关联手机号），国家码默认 +86：
 *   $env:CAMELTV_COUNTRY_CODE='+86'   # 可覆盖为其他区号
 *   CAMELTV_USERNAME 填手机号本地号（不带 +86）
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

/** 尽力而为地选中国家码（+86 等）。找不到控件时保持原样（账号可能已含国家码）。 */
async function applyCountryCode(page, countryCode) {
  if (!countryCode) return
  const digits = countryCode.replace(/\s+/g, '').replace(/^\+/, '')

  // 1) 原生 <select> 国家码下拉
  const select = page.locator('select').first()
  if (await select.isVisible().catch(() => false)) {
    const texts = await select.locator('option').allTextContents()
    const label =
      texts.find((t) => t.includes(`+${digits}`)) ||
      texts.find((t) => t.includes(digits) && t.includes('中国')) ||
      texts.find((t) => t.trim() === digits)
    if (label) {
      await select.selectOption({ label: label.trim() })
      return
    }
  }

  // 2) 自定义国家码下拉（按钮/触发器 → 选项）
  const trigger = page
    .locator(
      '[data-testid*="country" i], [aria-label*="国家" i], [aria-label*="区号" i], [aria-label*="country" i], [class*="country-code" i], [class*="area-code" i], button:has-text("+86")',
    )
    .first()
  if (await trigger.isVisible().catch(() => false)) {
    await trigger.click()
    const option = page
      .locator('[role="option"]:has-text("+86"), [role="option"]:has-text("中国"), li:has-text("+86"), div:has-text("+86")')
      .first()
    if (await option.isVisible().catch(() => false)) {
      await option.click()
    }
  }
}

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
  const countryCode = process.env.CAMELTV_COUNTRY_CODE?.trim() || '+86'

  const browser = await chromium.launch({ headless: true })
  try {
    const page = await browser.newPage()
    await page.goto(`${base}/login`, { waitUntil: 'domcontentloaded' })
    await applyCountryCode(page, countryCode)

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
