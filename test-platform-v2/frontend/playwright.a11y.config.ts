import { defineConfig } from '@playwright/test'

import baseConfig from './playwright.config'

const previewUrl = 'http://127.0.0.1:4173'

export default defineConfig({
  ...baseConfig,
  use: {
    ...baseConfig.use,
    baseURL: previewUrl,
  },
  webServer: {
    command: 'npm run preview -- --host 127.0.0.1 --port 4173',
    url: `${previewUrl}/login`,
    reuseExistingServer: false,
    timeout: 120_000,
    stdout: 'pipe',
    stderr: 'pipe',
  },
})
