import { defineConfig } from '@playwright/test'
import * as dotenv from 'dotenv'
import * as path from 'path'

import { getLoginCredentials } from './utils/auth'
import { parseRuntimePreconditions } from './utils/preconditions'

const environmentName = process.env.TEST_ENV?.trim()
if (environmentName) {
  dotenv.config({ path: path.resolve(__dirname, `.env.${environmentName}`) })
}
dotenv.config({ path: path.resolve(__dirname, '.env') })

const runtime = parseRuntimePreconditions()
getLoginCredentials()

export default defineConfig({
  testDir: './tests',
  testMatch: '**/*.spec.ts',
  timeout: 60_000,
  expect: {
    timeout: 15_000,
  },
  fullyParallel: false,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 2 : 0,
  workers: 1,
  reporter: [
    ['list'],
    ['html', { outputFolder: '../reports/html' }],
    ['json', { outputFile: '../reports/ui-test-results.json' }],
    ['junit', { outputFile: '../reports/ui-test-junit.xml' }],
  ],
  use: {
    baseURL: runtime.baseUrl.toString(),
    proxy: process.env.HTTP_PROXY
      ? { server: process.env.HTTP_PROXY }
      : undefined,
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    viewport: { width: 1280, height: 800 },
    locale: 'en-US',
  },
  projects: [
    {
      name: runtime.targetEnvironment,
      use: {
        baseURL: runtime.baseUrl.toString(),
      },
    },
  ],
})
