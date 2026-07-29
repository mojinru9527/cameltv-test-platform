import os from 'node:os'
import path from 'node:path'
import { defineConfig } from '@playwright/test'
import baseConfig from './playwright.config'

const outputRoot = path.join(
  process.env.TEMP || process.env.TMP || os.tmpdir(),
  'cameltv-batch56-playwright',
)

export default defineConfig(baseConfig, {
  outputDir: path.join(outputRoot, 'artifacts'),
  reporter: [
    ['list'],
    ['html', { open: 'never', outputFolder: path.join(outputRoot, 'html-report') }],
    ['json', { outputFile: path.join(outputRoot, 'e2e-results.json') }],
  ],
})
