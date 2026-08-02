import { expect, test } from '@playwright/test'

import {
  assertApiAssetsObserved,
  assertProductionRequestAllowed,
  readProductionSmokeRuntime,
  type ApiAssetObservation,
  type ProductionSmokeRuntime,
} from '../support/production-smoke-contract'

test.describe('CamelTv production web read-only smoke', () => {
  let runtime: ProductionSmokeRuntime

  test.beforeAll(() => {
    runtime = readProductionSmokeRuntime()
  })

  test('homepage, business fixture, and API evidence agree', async ({ page }) => {
    const apiAssets: ApiAssetObservation[] = []
    const rejectedMethods: string[] = []

    await page.route('**/*', async (route) => {
      const request = route.request()
      try {
        assertProductionRequestAllowed(runtime, request.url(), request.method())
      } catch (error) {
        rejectedMethods.push(error instanceof Error ? error.message : String(error))
        await route.abort('blockedbyclient')
        return
      }
      await route.continue()
    })
    page.on('response', (response) => {
      if (/\/api\/|api\./i.test(response.url())) {
        apiAssets.push({ url: response.url(), status: response.status() })
      }
    })

    const response = await page.goto(runtime.baseUrl.toString(), {
      waitUntil: 'networkidle',
    })

    expect(response?.status() ?? 0).toBeGreaterThanOrEqual(200)
    expect(response?.status() ?? 500).toBeLessThan(400)
    await expect(page.getByText(runtime.expectedBusinessText, { exact: false }).first()).toBeVisible()
    assertApiAssetsObserved(apiAssets)
    expect(rejectedMethods).toEqual([])
  })
})
