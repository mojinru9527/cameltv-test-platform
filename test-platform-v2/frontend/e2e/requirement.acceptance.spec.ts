import AxeBuilder from '@axe-core/playwright'
import { expect, test } from '@playwright/test'
import type { Page, Route } from '@playwright/test'

async function login(page: Page) {
  await page.goto('/requirement')
  await expect(page).toHaveURL(/\/login/)
  await page.fill('input[name="username"]', 'batch48-browser')
  await page.fill('input[type="password"]', 'local-contract-fixture')
  await page.click('button[type="submit"]')
  await expect(page).toHaveURL(/\/requirement/, { timeout: 15_000 })
}

function ok(route: Route, data: unknown) {
  return route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ code: 0, msg: 'ok', data }),
  })
}

test.describe('Batch 48 requirement browser contract', () => {
  test('upload, lazy preview, one initial GET, keyboard and responsive journey', async ({ page }) => {
    const consoleErrors: string[] = []
    const listRequests: string[] = []
    const unique = `batch48-browser-${Date.now()}`
    const document = {
      id: 48001,
      title: unique,
      source_ref: `${unique}.md`,
      file_type: 'md',
      status: 'uploaded',
      extraction_status: 'none',
      imported_count: 0,
      imported_func_count: 0,
      imported_api_count: 0,
      creator_id: 48,
      creator_name: 'Batch 48 Browser',
      created_at: '2026-07-27T08:00:00Z',
      updated_at: '2026-07-27T08:00:00Z',
      content: `# ${unique}\n\n${unique}-正文标记`,
    }
    const secondPageDocument = {
      ...document,
      id: 48011,
      title: `${unique}-第二页审查`,
      source_ref: `${unique}-第二页审查.md`,
      status: 'generated',
      extraction_status: 'confirmed',
      content: `# ${unique}-第二页审查\n\n移动端跨页正文`,
    }
    const pagedDocuments = [
      document,
      ...Array.from({ length: 9 }, (_, index) => ({
        ...document,
        id: 48002 + index,
        title: `${unique}-列表-${index + 1}`,
        source_ref: `${unique}-列表-${index + 1}.md`,
        content: `# ${unique}-列表-${index + 1}`,
      })),
      secondPageDocument,
    ]
    let uploaded = false

    await page.route('**/api/v1/**', async (route) => {
      const request = route.request()
      const url = new URL(request.url())
      const apiPath = url.pathname.replace('/api/v1', '')

      if (apiPath === '/auth/login' && request.method() === 'POST') {
        return ok(route, {
          access_token: 'browser-contract-token',
          token_type: 'bearer',
          user: {
            id: 48,
            username: 'batch48-browser',
            nickname: 'Batch 48 Browser',
            email: 'batch48@example.invalid',
          },
          projects: [{ id: 48, code: 'batch48', name: 'Batch 48 隔离项目' }],
          permissions: ['*'],
          must_change_password: false,
        })
      }
      if (apiPath === '/system/menus') return ok(route, [])
      if (apiPath === '/test-cases/domains') return ok(route, [])
      if (apiPath === '/requirements' && request.method() === 'GET') {
        const keyword = url.searchParams.get('keyword')?.toLocaleLowerCase() || ''
        const pageNumber = Number(url.searchParams.get('page') || 1)
        const pageSize = Number(url.searchParams.get('page_size') || 10)
        const matchingDocuments = (uploaded ? pagedDocuments : [])
          .filter((item) => item.title.toLocaleLowerCase().includes(keyword))
        const start = (pageNumber - 1) * pageSize
        return ok(route, {
          total: matchingDocuments.length,
          page: pageNumber,
          page_size: pageSize,
          items: matchingDocuments
            .slice(start, start + pageSize)
            .map((item) => ({ ...item, content: undefined })),
        })
      }
      if (apiPath === '/requirements/upload' && request.method() === 'POST') {
        uploaded = true
        return ok(route, document)
      }
      const documentMatch = apiPath.match(/^\/requirements\/(\d+)$/)
      if (documentMatch && request.method() === 'GET') {
        const requested = pagedDocuments.find(
          (item) => item.id === Number(documentMatch[1]),
        )
        return ok(route, requested || null)
      }
      if (/^\/requirements\/\d+\/coverage$/.test(apiPath)) {
        return ok(route, {
          document_id: document.id,
          total_requirements: 4,
          covered_requirements: 3,
          coverage_rate: 75,
        })
      }
      if (
        apiPath === `/requirements/${secondPageDocument.id}/review-state`
        && request.method() === 'GET'
      ) {
        return ok(route, {
          document_id: secondPageDocument.id,
          document_title: secondPageDocument.title,
          functional_cases: [{
            index: 0,
            title: '移动端审查用例',
            module: '需求服务',
            priority: 'P0',
            preconditions: '已进入审查页',
            steps: '[]',
            expected_result: '审查队列可见',
            review_status: 'pending',
          }],
          api_cases: [],
          summary: {},
        })
      }
      if (apiPath === `/requirements/${document.id}` && request.method() === 'DELETE') {
        uploaded = false
        return ok(route, { id: document.id })
      }
      return ok(route, {})
    })

    page.on('console', (message) => {
      if (message.type() === 'error') consoleErrors.push(message.text())
    })
    page.on('request', (request) => {
      const url = new URL(request.url())
      if (
        request.method() === 'GET'
        && url.pathname === '/api/v1/requirements'
      ) {
        listRequests.push(`${url.pathname}${url.search}`)
      }
    })

    await login(page)
    await expect(page.getByText('需求文档记录')).toBeVisible()
    await expect.poll(() => listRequests.length).toBe(1)

    await page.locator('input[type="file"]').setInputFiles({
      name: `${unique}.md`,
      mimeType: 'text/markdown',
      buffer: Buffer.from(`# ${unique}\n\n${unique}-正文标记`, 'utf8'),
    })

    const previewButton = page.getByRole('button', {
      name: `预览需求文档：${unique}`,
      exact: true,
    })
    await expect(previewButton).toBeVisible()
    await expect(page.getByText(`${unique}-正文标记`)).toBeVisible()

    try {
      for (const viewport of [
        { width: 1440, height: 900 },
        { width: 768, height: 1024 },
        { width: 390, height: 844 },
      ]) {
        await page.setViewportSize(viewport)
        await expect(previewButton).toBeVisible()
        const hasGlobalOverflow = await page.evaluate(
          () => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1,
        )
        expect(hasGlobalOverflow).toBe(false)
        if (process.env.E2E_EVIDENCE_DIR) {
          await page.screenshot({
            path: `${process.env.E2E_EVIDENCE_DIR}/requirement-${viewport.width}x${viewport.height}.png`,
            fullPage: true,
          })
        }
      }

      await previewButton.focus()
      await page.keyboard.press('Enter')
      await expect(previewButton).toHaveAttribute('aria-pressed', 'true')

      await page.locator('button[aria-label="下一页"]:not([disabled])').click()
      const secondPagePreview = page.getByRole('button', {
        name: `预览需求文档：${secondPageDocument.title}`,
        exact: true,
      })
      await expect(secondPagePreview).toBeVisible()
      expect(listRequests.some((request) => request.includes('page=2'))).toBe(true)

      await page.getByPlaceholder('搜索文档').fill(secondPageDocument.title)
      await expect.poll(
        () => listRequests.some(
          (request) => decodeURIComponent(request)
            .includes(`keyword=${secondPageDocument.title}`),
        ),
      ).toBe(true)
      await expect(secondPagePreview).toBeVisible()

      await secondPagePreview.focus()
      await page.keyboard.press('Space')
      await expect(secondPagePreview).toHaveAttribute('aria-pressed', 'true')

      const secondPageRow = page.getByRole('row').filter({ has: secondPagePreview })
      await secondPageRow.getByRole('button', { name: '审查用例' }).click()
      await expect(page).toHaveURL(
        new RegExp(`/requirement/${secondPageDocument.id}/review$`),
      )
      await expect(
        page.getByRole('heading', { name: secondPageDocument.title }),
      ).toBeVisible()
      await page.getByRole('button', { name: '返回', exact: true }).click()
      await expect(page).toHaveURL(/\/requirement$/)
      await expect(previewButton).toBeVisible()

      const a11y = await new AxeBuilder({ page })
        .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
        .analyze()
      expect(a11y.violations).toEqual([])
      expect(consoleErrors).toEqual([])
    } finally {
      const row = page.getByRole('row').filter({ has: previewButton })
      await row.getByRole('button', { name: '删除' }).click()
      const dialog = page.getByRole('alertdialog')
      await dialog.getByRole('button', { name: '删除' }).click()
      await expect(previewButton).toHaveCount(0)
    }
  })
})
