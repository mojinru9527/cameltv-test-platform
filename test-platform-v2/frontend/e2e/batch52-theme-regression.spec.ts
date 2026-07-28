import AxeBuilder from '@axe-core/playwright'
import { mkdirSync } from 'node:fs'
import path from 'node:path'
import { expect, test, type Page, type Route, type TestInfo } from '@playwright/test'

const THEMES = [
  { id: 'cyberpunk', label: '01 赛博' },
  { id: 'apple', label: '02 晶穹' },
  { id: 'clay', label: '03 软体' },
  { id: 'xlab', label: '04 黑域' },
  { id: 'liquid-glass', label: '05 液境' },
  { id: 'obsidian-flow', label: '06 黑曜' },
] as const

const VIEWPORTS = [
  { id: 'mobile', width: 390, height: 844 },
  { id: 'tablet', width: 768, height: 1024 },
  { id: 'desktop', width: 1440, height: 900 },
] as const

const DASHBOARD_STATS = {
  total_cases: 128,
  total_plans: 12,
  api_cases: 86,
  pass_rate: 96.8,
  case_type_stats: [],
  priority_distribution: [],
  time_range: null,
}

function ok(route: Route, data: unknown) {
  return route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ code: 0, msg: 'ok', data }),
  })
}

async function installFixtures(page: Page, colorTheme?: string) {
  await page.emulateMedia({ colorScheme: 'dark', reducedMotion: 'reduce' })
  await page.addInitScript(({ storedTheme }) => {
    localStorage.setItem('cameltv-auth', JSON.stringify({
      state: {
        user: {
          id: 52,
          username: 'batch52-ui',
          nickname: 'Batch 52 UI',
          email: 'batch52-ui@example.invalid',
        },
        projects: [{ id: 52, code: 'batch52', name: 'Batch 52 黑曜验收项目' }],
        permissions: ['*'],
        currentProjectId: 52,
        projectThemeMap: {},
      },
      version: 0,
    }))
    localStorage.removeItem('cameltv-ui-theme')
    localStorage.removeItem('cameltv-theme-mode')
    localStorage.removeItem('cameltv-theme-color')
    if (storedTheme) {
      localStorage.setItem('cameltv-theme-mode', 'dark')
      localStorage.setItem('cameltv-theme-color', storedTheme)
    }
  }, { storedTheme: colorTheme })

  await page.route('**/api/v1/**', async (route) => {
    const request = route.request()
    const apiPath = new URL(request.url()).pathname.replace(/^\/api\/v1/, '')
    if (request.method() !== 'GET') return route.abort('blockedbyclient')
    if (apiPath === '/system/menus') {
      return ok(route, [
        {
          id: 1,
          code: 'menu:workbench',
          name: '工作台',
          path: '/workbench',
          icon: 'DashboardOutlined',
          sort: 1,
        },
      ])
    }
    if (apiPath === '/dashboard/stats') return ok(route, DASHBOARD_STATS)
    return route.abort('blockedbyclient')
  })
}

async function openWorkbench(page: Page) {
  await page.goto('/workbench')
  await expect(page.getByRole('heading', { level: 1, name: '工作台', exact: true })).toHaveCount(1)
  await page.waitForLoadState('networkidle')
}

function screenshotPath(testInfo: TestInfo, name: string) {
  const evidenceDir = process.env.E2E_EVIDENCE_DIR
  if (!evidenceDir) return testInfo.outputPath(name)
  mkdirSync(evidenceDir, { recursive: true })
  return path.join(evidenceDir, name)
}

test.describe('Batch 52 unified production theme contract', () => {
  test('keeps Obsidian Flow as the first-paint default without legacy storage', async ({ page }) => {
    await installFixtures(page)
    await openWorkbench(page)

    const root = page.locator('html')
    await expect(root).toHaveAttribute('data-theme', 'obsidian-flow')
    await expect(root).toHaveAttribute('data-theme-id', 'obsidian-flow')
    await expect(root).toHaveAttribute('data-ui-theme', 'obsidian-flow')
    await expect(root).toHaveClass(/dark/)
  })

  test('switches all six themes through one state contract with distinct token signatures', async ({
    page,
  }) => {
    await installFixtures(page, 'obsidian-flow')
    await openWorkbench(page)

    const signatures = new Map<string, string>()
    for (const theme of THEMES) {
      const trigger = page.getByRole('button', { name: /^切换主题/ })
      if (!(await page.getByText('主题风格', { exact: true }).isVisible().catch(() => false))) {
        await trigger.click()
      }

      await page.locator('button').filter({ hasText: theme.label }).click()
      const root = page.locator('html')
      await expect(root).toHaveAttribute('data-theme', theme.id)
      await expect(root).toHaveAttribute('data-theme-id', theme.id)

      if (theme.id === 'obsidian-flow') {
        await expect(root).toHaveAttribute('data-ui-theme', 'obsidian-flow')
        await expect(root).toHaveClass(/dark/)
      } else {
        await expect(root).not.toHaveAttribute('data-ui-theme', /.+/)
      }

      const signature = await page.evaluate(() => {
        const style = getComputedStyle(document.documentElement)
        return ['--background', '--foreground', '--primary', '--card', '--border']
          .map((token) => style.getPropertyValue(token).trim())
          .join('|')
      })
      expect(signature, `${theme.id} must expose production color tokens`).not.toBe('||||')
      signatures.set(theme.id, signature)
    }

    expect(new Set(signatures.values()).size).toBe(THEMES.length)
  })

  for (const viewport of VIEWPORTS) {
    test(`Obsidian ${viewport.id}: responsive, accessible and visually stable`, async ({
      page,
    }, testInfo) => {
      const consoleErrors: string[] = []
      const pageErrors: string[] = []
      page.on('console', (message) => {
        if (message.type() === 'error') consoleErrors.push(message.text())
      })
      page.on('pageerror', (error) => pageErrors.push(error.message))

      await installFixtures(page, 'obsidian-flow')
      await page.setViewportSize(viewport)
      await openWorkbench(page)

      const overflow = await page.evaluate(
        () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
      )
      expect(overflow).toBeLessThanOrEqual(1)
      const themeTrigger = page.getByRole('button', { name: /^切换主题，当前黑曜/ })
      await expect(themeTrigger).toBeVisible()

      if (viewport.id === 'mobile') {
        for (const { name, control } of [
          { name: 'theme trigger', control: themeTrigger },
          { name: 'sidebar trigger', control: page.getByRole('button', { name: 'Toggle Sidebar' }) },
          { name: 'user menu', control: page.getByRole('button', { name: /^用户菜单：/ }) },
          { name: 'project selector', control: page.getByRole('combobox', { name: '当前项目' }) },
        ]) {
          const box = await control.boundingBox()
          expect(box?.width, `${name} width`).toBeGreaterThanOrEqual(44)
          expect(box?.height, `${name} height`).toBeGreaterThanOrEqual(44)
        }
      }

      if (viewport.id === 'desktop') {
        const results = await new AxeBuilder({ page })
          .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
          .analyze()
        expect(
          results.violations.map(({ id, impact, nodes }) => ({
            id,
            impact,
            nodes: nodes.length,
            targets: nodes.slice(0, 5).map((node) => node.target),
          })),
        ).toEqual([])
      }

      await page.screenshot({
        path: screenshotPath(
          testInfo,
          `batch52-obsidian-${viewport.id}-${viewport.width}x${viewport.height}.png`,
        ),
        fullPage: true,
        animations: 'disabled',
        caret: 'hide',
      })

      expect(consoleErrors).toEqual([])
      expect(pageErrors).toEqual([])
    })
  }
})
