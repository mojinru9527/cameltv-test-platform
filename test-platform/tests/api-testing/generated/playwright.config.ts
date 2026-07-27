import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './',
  testMatch: '**/*.spec.ts',
  retries: 1,
  timeout: 30000,
  expect: { timeout: 10000 },
  // outputFile 优先读取 runner 注入的绝对路径（JUNIT_OUTPUT / JSON_OUTPUT），
  // 未注入时回退到相对路径（手动 npx playwright test 时仍可用）
  reporter: [
    ['list'],
    ['junit', { outputFile: process.env.JUNIT_OUTPUT || '../../api-testing/reports/api-test-junit.xml' }],
    ['json', { outputFile: process.env.JSON_OUTPUT || '../../api-testing/reports/api-test-results.json' }],
  ],
  use: {
    baseURL: process.env.CAMELTV_BASE_URL || 'http://localhost:8000',
    extraHTTPHeaders: {
      'Authorization': `Bearer ${process.env.CAMELTV_AUTH_TOKEN || ''}`,
    },
    proxy: process.env.HTTP_PROXY ? {
      server: process.env.HTTP_PROXY,
    } : undefined,
    trace: 'on-first-retry',
  },
});
