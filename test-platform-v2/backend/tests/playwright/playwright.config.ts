import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './specs',
  timeout: 300000,          // 5min per test (match backend DEFAULT_TIMEOUT)
  retries: 0,
  reporter: [
    ['json', { outputFile: 'report.json' }],
    ['html', { open: 'never' }],
    ['list'],
  ],
  outputDir: './artifacts',
  use: {
    baseURL: process.env.BASE_URL || 'https://cameltv.com',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    trace: 'retain-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },
    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
    },
  ],
});
