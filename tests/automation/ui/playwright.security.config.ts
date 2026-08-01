import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './tests/security',
  fullyParallel: false,
  workers: 1,
  reporter: 'list',
})
