/**
 * AITDE V3 e2e 共享助手（v331-remediation-2 C1）。
 *
 * 前置条件：
 *   1. 后端运行于 VITE_PROXY_TARGET（默认 127.0.0.1:8341），AITDE_V3_ENABLED=true
 *   2. 前端 dev server 运行于 5441，VITE_AITDE_V3_ENABLED=true
 *   3. E2E_USERNAME / E2E_PASSWORD 注入登录账号
 *
 * 运行（backend 与 frontend 已启动时，frontend/ 目录下）：
 *   E2E_USERNAME=admin E2E_PASSWORD=... npx playwright test e2e/aitde-v3-*.spec.ts
 */
import { expect, type Page } from '@playwright/test'

export const ADMIN = {
  username: process.env.E2E_USERNAME || '',
  password: process.env.E2E_PASSWORD || '',
}

export const HAS_AUTH = Boolean(ADMIN.username && ADMIN.password)

/** 登录并等待跳转工作台。 */
export async function login(page: Page): Promise<void> {
  await page.goto('/login')
  await page.fill('input[name="username"]', ADMIN.username)
  await page.fill('input[type="password"]', ADMIN.password)
  await page.click('button[type="submit"]')
  await expect(page).toHaveURL(/\/workbench/, { timeout: 15_000 })
}

/**
 * 登录后进入项目上下文。
 * setLogin 会自动选中账号的第一个项目（seed 默认项目 id=1，即 v2 端点
 * 要求的 X-Project-Id）；AITDE_V3 开启时 v2 端点才可达。
 */
export async function loginAndPickProject(page: Page): Promise<void> {
  await login(page)
}
