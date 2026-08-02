import { promises as fs } from 'node:fs'
import { tmpdir } from 'node:os'
import path from 'node:path'

import { expect, test } from '@playwright/test'
import type { Page } from '@playwright/test'

import {
  fillLoginForm,
  getLoginCredentials,
} from '../../utils/auth'
import {
  assertNoCanaryLeak,
  attachTrafficCapture,
  flushTrafficCapture,
  initTrafficCapture,
} from '../../utils/traffic-capture'

const uiRoot = path.resolve(__dirname, '../..')

test.describe('auth security contract', () => {
  const originalUsername = process.env.CAMELTV_USERNAME
  const originalPassword = process.env.CAMELTV_PASSWORD

  test.afterEach(() => {
    if (originalUsername === undefined) delete process.env.CAMELTV_USERNAME
    else process.env.CAMELTV_USERNAME = originalUsername
    if (originalPassword === undefined) delete process.env.CAMELTV_PASSWORD
    else process.env.CAMELTV_PASSWORD = originalPassword
  })

  test('missing credentials fail explicitly and no default account is used', () => {
    delete process.env.CAMELTV_USERNAME
    delete process.env.CAMELTV_PASSWORD

    expect(() => getLoginCredentials()).toThrow(/CAMELTV_USERNAME.*CAMELTV_PASSWORD/)
  })

  test('credentials are filled through deterministic Playwright locators', async () => {
    const fills: Array<{ selector: string; value: string }> = []
    let clickedSelector = ''

    const fakePage = {
      locator(selector: string) {
        return {
          first() {
            return this
          },
          async waitFor() {},
          async fill(value: string) {
            fills.push({ selector, value })
          },
          async click() {
            clickedSelector = selector
          },
        }
      },
    } as unknown as Page

    await fillLoginForm(fakePage, {
      username: 'real-user@example.test',
      password: 'real-password-value',
    })

    expect(fills).toEqual([
      {
        selector: expect.stringContaining('input'),
        value: 'real-user@example.test',
      },
      {
        selector: expect.stringContaining('password'),
        value: 'real-password-value',
      },
    ])
    expect(clickedSelector).toContain('submit')
  })

  test('auth source never passes credentials to Midscene or other AI instructions', async () => {
    const source = await fs.readFile(path.join(uiRoot, 'utils/auth.ts'), 'utf8')

    expect(source).not.toContain('@midscene/web')
    expect(source).not.toContain("|| 'qa_test'")
    expect(source).not.toMatch(/ai(?:Action|Boolean)\s*\([^)]*(?:username|password)/s)
  })
})

type PageHandler = (value: any) => void

class FakeCapturePage {
  private readonly handlers = new Map<string, PageHandler[]>()

  on(event: string, handler: PageHandler) {
    const handlers = this.handlers.get(event) ?? []
    handlers.push(handler)
    this.handlers.set(event, handlers)
    return this
  }

  emit(event: string, value: any) {
    for (const handler of this.handlers.get(event) ?? []) handler(value)
  }
}

test.describe('traffic capture security contract', () => {
  let outputDir = ''
  const originalOutputDir = process.env.CAPTURE_OUTPUT_DIR

  test.beforeEach(async () => {
    outputDir = await fs.mkdtemp(path.join(tmpdir(), 'cameltv-ui-capture-'))
    process.env.CAPTURE_OUTPUT_DIR = outputDir
  })

  test.afterEach(async () => {
    if (originalOutputDir === undefined) delete process.env.CAPTURE_OUTPUT_DIR
    else process.env.CAPTURE_OUTPUT_DIR = originalOutputDir
    await fs.rm(outputDir, { recursive: true, force: true })
  })

  test('deeply redacts URL, query, headers, request body, and response body', async () => {
    const page = new FakeCapturePage()
    initTrafficCapture('security-redaction')
    attachTrafficCapture(page as unknown as Page)

    const request = {
      url: () => 'https://example.test/api/session/path-secret?access_token=query-secret&safe=visible',
      method: () => 'POST',
      headers: () => ({
        authorization: 'Bearer header-secret',
        cookie: 'session=cookie-secret',
        'x-api-key': 'api-key-secret',
        'x-safe-header': 'visible',
      }),
      postDataJSON: () => ({
        username: 'visible-user',
        password: 'body-password',
        nested: {
          refreshToken: 'nested-token',
          safe: 'visible-value',
        },
      }),
      postData: () => null,
    }
    page.emit('request', request)
    page.emit('response', {
      request: () => request,
      status: () => 200,
      json: async () => ({
        data: {
          sessionId: 'response-session',
          api_secret: 'response-secret',
          safe: 'visible-response',
        },
      }),
    })

    await flushTrafficCapture()

    const [captureFile] = await fs.readdir(outputDir)
    const raw = await fs.readFile(path.join(outputDir, captureFile), 'utf8')
    const entry = JSON.parse(raw)

    for (const secret of [
      'query-secret',
      'path-secret',
      'header-secret',
      'cookie-secret',
      'api-key-secret',
      'body-password',
      'nested-token',
      'response-session',
      'response-secret',
    ]) {
      expect(raw).not.toContain(secret)
    }
    expect(entry.url).toContain('access_token=%5BREDACTED%5D')
    expect(entry.path).toBe('/api/session/%5BREDACTED%5D')
    expect(entry.query).toEqual({ access_token: '[REDACTED]', safe: 'visible' })
    expect(entry.headers.authorization).toBe('[REDACTED]')
    expect(entry.headers['x-safe-header']).toBe('visible')
    expect(entry.body.nested).toEqual({
      refreshToken: '[REDACTED]',
      safe: 'visible-value',
    })
    expect(entry.response_body.data).toEqual({
      sessionId: '[REDACTED]',
      api_secret: '[REDACTED]',
      safe: 'visible-response',
    })
  })

  test('starting a new session clears prior captured entries', async () => {
    const page = new FakeCapturePage()
    initTrafficCapture('first-session')
    attachTrafficCapture(page as unknown as Page)
    page.emit('request', {
      url: () => 'https://example.test/api/safe',
      method: () => 'GET',
      headers: () => ({}),
      postDataJSON: () => null,
      postData: () => null,
    })
    await flushTrafficCapture()

    initTrafficCapture('empty-second-session')
    await flushTrafficCapture()

    expect(await fs.readdir(outputDir)).toHaveLength(1)
  })

  test('canary scan rejects sensitive values even under an innocent field name', () => {
    expect(() =>
      assertNoCanaryLeak(
        JSON.stringify({ safe: 'batch61-canary-secret' }),
        ['batch61-canary-secret'],
      ),
    ).toThrow(/evidence canary/i)

    expect(() =>
      assertNoCanaryLeak(
        JSON.stringify({ correlation_id: 'batch61-correlation-001' }),
        ['batch61-canary-secret'],
      ),
    ).not.toThrow()
  })
})

test('package scripts use supported Playwright environment selection', async () => {
  const packageJson = JSON.parse(
    await fs.readFile(path.join(uiRoot, 'package.json'), 'utf8'),
  )

  expect(packageJson.scripts['test:test']).toContain('TEST_ENV=test')
  expect(packageJson.scripts['test:prod']).toContain('TEST_ENV=prod')
  expect(packageJson.scripts['test:test']).not.toContain('--env')
  expect(packageJson.scripts['test:prod']).not.toContain('--env')
})

test('main Playwright config and env template contain no implicit target or account', async () => {
  const configSource = await fs.readFile(
    path.join(uiRoot, 'playwright.config.ts'),
    'utf8',
  )
  const envExample = await fs.readFile(path.join(uiRoot, '.env.example'), 'utf8')

  for (const source of [configSource, envExample]) {
    expect(source).not.toContain('https://g3-test3.elelive.cn')
    expect(source).not.toContain('CAMELTV_USERNAME=qa_test')
  }
  expect(configSource).toContain('parseRuntimePreconditions')
  expect(configSource).toContain('getLoginCredentials')
})

test('sports business specs use stable data and API oracles without silent skips', async () => {
  const businessSpecs = [
    'tests/home/home-recommend.spec.ts',
    'tests/list/article-list.spec.ts',
    'tests/detail/article-detail.spec.ts',
    'tests/pay/recharge.spec.ts',
    'tests/refund/first-bet-protection.spec.ts',
    'tests/bonus/bonus-camel-coins.spec.ts',
  ]

  for (const relativePath of businessSpecs) {
    const source = await fs.readFile(path.join(uiRoot, relativePath), 'utf8')
    expect(source, relativePath).not.toContain('test.skip')
    expect(source, relativePath).not.toContain('console.log')
    expect(source, relativePath).toContain('requireStringTestData')
    expect(source, relativePath).toContain('observeSuccessfulApi')
  }
})
