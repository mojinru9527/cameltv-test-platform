import { defineConfig, devices } from '@playwright/test'

/**
 * Playwright E2E 配置 — 测试平台 v2 前端冒烟测试。
 *
 * 运行方式：
 *   npx playwright test                    # headless (CI)
 *   npx playwright test --headed           # 可视调试
 *   npx playwright test --project=chromium # 单浏览器
 *
 * 前置条件：后端 (uvicorn) + 前端 (vite) 均已启动。
 * 默认 BASE_URL=http://localhost:5173（vite dev server）。
 */
export default defineConfig({
  testDir: './e2e',
  timeout: 30_000,
  expect: { timeout: 10_000 },
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 1,
  reporter: [
    ['list'],
    ['html', { open: 'never' }],
    ['json', { outputFile: 'test-results/e2e-results.json' }],
  ],
  use: {
    baseURL: process.env.BASE_URL || 'http://localhost:5173',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
})
