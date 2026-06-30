import { defineConfig } from '@playwright/test';
import * as dotenv from 'dotenv';
import * as path from 'path';

// Load environment-specific .env
const env = process.env.TEST_ENV || 'test';
dotenv.config({ path: path.resolve(__dirname, `.env.${env}`) });
dotenv.config({ path: path.resolve(__dirname, '.env') });

const BASE_URL = process.env.CAMELTV_BASE_URL || 'https://g3-test3.elelive.cn';

export default defineConfig({
  testDir: './tests',
  testMatch: '**/*.spec.ts',
  timeout: 60000,
  expect: {
    timeout: 15000,
  },
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 1,

  reporter: [
    ['list'],
    ['html', { outputFolder: '../reports/html' }],
    ['json', { outputFile: '../reports/ui-test-results.json' }],
    ['junit', { outputFile: '../reports/ui-test-junit.xml' }],
  ],

  use: {
    baseURL: BASE_URL,
    proxy: process.env.HTTP_PROXY ? { server: process.env.HTTP_PROXY } : undefined,
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    viewport: { width: 1280, height: 800 },
    locale: 'en-US',
  },

  projects: [
    {
      name: 'test',
      use: {
        baseURL: process.env.CAMELTV_BASE_URL || 'https://g3-test3.elelive.cn',
      },
    },
  ],
});
