# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: production-p0-modules.spec.ts >> 体育平台 生产 P0 功能用例 → UI 自动化（只读） >> P0-UI-006 我的：Login 引导 + 资产/功能入口渲染
- Location: specs\production-p0-modules.spec.ts:115:7

# Error details

```
Error: expect(locator).toBeVisible() failed

Locator: getByText(/Login|登录/i).first()
Expected: visible
Timeout: 5000ms
Error: element(s) not found

Call log:
  - Expect "toBeVisible" with timeout 5000ms
  - waiting for getByText(/Login|登录/i).first()

```

```yaml
- alert
- text: "11025728"
- link:
  - /url: /my/user
- button "Silver Diamond ..."
- list:
  - listitem:
    - button "Free Silver Diamond"
  - listitem:
    - button "Camel Mall"
- list:
  - listitem:
    - button "My Favorites"
  - listitem:
    - button "My Outfits"
  - listitem:
    - button "FAQ & Feedback"
  - listitem:
    - button "Business Cooperation"
  - listitem:
    - button "Settings"
- link "index User Feedback camellivefeedback@gmail.com":
  - /url: mailto:camellivefeedback@gmail.com
  - img "index"
  - heading "User Feedback" [level=3]
  - text: camellivefeedback@gmail.com
- link "index Business Cooperation camelsportstv@gmail.com":
  - /url: mailto:camelsportstv@gmail.com
  - img "index"
  - heading "Business Cooperation" [level=3]
  - text: camelsportstv@gmail.com
- link "index Join Our Telegram Free picks Never miss a goal":
  - /url: https://tinyurl.com/srf52pur
  - img "index"
  - text: Join Our Telegram Free picks Never miss a goal
- text: ;
```

# Test source

```ts
  18  |       return
  19  |     } catch (error) {
  20  |       rejected.push(error instanceof Error ? error.message : String(error))
  21  |       await route.abort('blockedbyclient')
  22  |     }
  23  |   })
  24  |   return rejected
  25  | }
  26  | 
  27  | function apiObservations(page: Page): string[] {
  28  |   const urls: string[] = []
  29  |   page.on('response', (response) => {
  30  |     if (API_URL_PATTERN.test(response.url())) {
  31  |       urls.push(response.url())
  32  |     }
  33  |   })
  34  |   return urls
  35  | }
  36  | 
  37  | test.describe('体育平台 生产 P0 功能用例 → UI 自动化（只读）', () => {
  38  |   let runtime: P0Runtime
  39  | 
  40  |   test.beforeAll(() => {
  41  |     runtime = readP0Runtime()
  42  |   })
  43  | 
  44  |   test.beforeEach(async ({ page }) => {
  45  |     page.setDefaultTimeout(20_000)
  46  |     page.setDefaultNavigationTimeout(30_000)
  47  |   })
  48  | 
  49  |   test.afterEach(async ({ page }, testInfo) => {
  50  |     const dir = process.env.P0_EVIDENCE_DIR || 'p0-evidence'
  51  |     await page
  52  |       .screenshot({
  53  |         path: `${dir}/${testInfo.title.replace(/[^\w\u4e00-\u9fa5-]/g, '_').slice(0, 80)}.png`,
  54  |         fullPage: false,
  55  |       })
  56  |       .catch(() => undefined)
  57  |   })
  58  | 
  59  |   test('P0-UI-001 首页：Live Matches/搜索/REGISTER + 核心 API 资产', async ({ page }) => {
  60  |     const rejected = await guardP0(page, runtime)
  61  |     const apiUrls = apiObservations(page)
  62  |     const response = await page.goto(runtime.baseUrl.toString(), { waitUntil: 'networkidle' })
  63  |     expect(response?.status() ?? 0).toBeGreaterThanOrEqual(200)
  64  |     await expect(page.getByText(/Live Matches|Favorites|Competitions/i).first()).toBeVisible()
  65  |     await expect(page.locator('input[type="text"], input[type="search"]').first()).toBeVisible()
  66  |     await expect(page.getByText(/REGISTER|Register/i).first()).toBeVisible()
  67  |     expect(apiUrls.some((u) => /ads\/activity|search\/hot|client\/general/i.test(u))).toBe(true)
  68  |     expect(rejected).toEqual([])
  69  |   })
  70  | 
  71  |   test('P0-UI-002 赛事详情：标题/比分/标签渲染', async ({ page }) => {
  72  |     const rejected = await guardP0(page, runtime)
  73  |     await page.goto(new URL('/football/as-monaco-vs-getafe/n54qllhn0vwjqvy', runtime.baseUrl).toString(), {
  74  |       waitUntil: 'domcontentloaded',
  75  |     })
  76  |     await expect(page.getByText(/AS Monaco|Getafe|Monaco/i).first()).toBeVisible()
  77  |     const headings = await page.locator('h1,h2,h3').allTextContents()
  78  |     expect(headings.join(' ').length).toBeGreaterThan(10)
  79  |     expect(rejected).toEqual([])
  80  |   })
  81  | 
  82  |   test('P0-UI-003 直播间：视频容器/直播页面渲染', async ({ page }) => {
  83  |     const rejected = await guardP0(page, runtime)
  84  |     await page.goto(new URL('/football/persatuan-sepakbola-indonesia-jakarta-vs-arema-fc/live/2y8m4zh5kwgpql0', runtime.baseUrl).toString(), {
  85  |       waitUntil: 'domcontentloaded',
  86  |     })
  87  |     await expect(page.locator('[class*="roomLive"]').first()).toBeVisible()
  88  |     await expect(page.getByText(/Live Streaming|Live Score/i).first()).toBeVisible()
  89  |     expect(rejected).toEqual([])
  90  |   })
  91  | 
  92  |   test('P0-UI-004 资讯：列表 + 首条资讯详情可达', async ({ page }) => {
  93  |     const rejected = await guardP0(page, runtime)
  94  |     await page.goto(new URL('/q/news', runtime.baseUrl).toString(), { waitUntil: 'networkidle' })
  95  |     const articleLinks = page.locator('a[href*="/news/detail/"]')
  96  |     await expect(articleLinks.first()).toBeVisible()
  97  |     const href = await articleLinks.first().getAttribute('href')
  98  |     expect(href).toBeTruthy()
  99  |     expect(rejected).toEqual([])
  100 |   })
  101 | 
  102 |   test('P0-UI-005 搜索：输入查询并看到结果（查询型 POST 放行）', async ({ page }) => {
  103 |     const rejected = await guardP0(page, runtime)
  104 |     await page.goto(new URL('/search', runtime.baseUrl).toString(), { waitUntil: 'domcontentloaded' })
  105 |     const input = page.locator('input[type="text"], input[type="search"]').first()
  106 |     await expect(input).toBeVisible()
  107 |     await input.fill('Real Madrid')
  108 |     await page.keyboard.press('Enter')
  109 |     await page.waitForTimeout(2500)
  110 |     const bodyText = await page.locator('body').innerText()
  111 |     expect(/Real Madrid|real madrid/i.test(bodyText)).toBe(true)
  112 |     expect(rejected).toEqual([])
  113 |   })
  114 | 
  115 |   test('P0-UI-006 我的：Login 引导 + 资产/功能入口渲染', async ({ page }) => {
  116 |     const rejected = await guardP0(page, runtime)
  117 |     await page.goto(new URL('/my', runtime.baseUrl).toString(), { waitUntil: 'domcontentloaded' })
> 118 |     await expect(page.getByText(/Login|登录/i).first()).toBeVisible()
      |                                                       ^ Error: expect(locator).toBeVisible() failed
  119 |     await expect(page.getByText(/Silver Diamond|Camel Mall|Favorites|Outfits|FAQ/i).first()).toBeVisible()
  120 |     expect(rejected).toEqual([])
  121 |   })
  122 | 
  123 |   test('P0-UI-007 联赛：积分榜/赛程表面渲染', async ({ page }) => {
  124 |     const rejected = await guardP0(page, runtime)
  125 |     await page.goto(new URL('/r/league/UEFA%20Europa%20League', runtime.baseUrl).toString(), { waitUntil: 'domcontentloaded' })
  126 |     await expect(page.getByText(/UEFA Europa League/i).first()).toBeVisible()
  127 |     const bodyText = await page.locator('body').innerText()
  128 |     expect(/Standings|Schedule|Fixture/i.test(bodyText)).toBe(true)
  129 |     expect(rejected).toEqual([])
  130 |   })
  131 | 
  132 |   test('P0-UI-008 回放：列表渲染记录', async ({ page }) => {
  133 |     const rejected = await guardP0(page, runtime)
  134 |     await page.goto(new URL('/match-replay', runtime.baseUrl).toString(), { waitUntil: 'networkidle' })
  135 |     const replayLinks = page.locator('a[href*="/match-replay/"]')
  136 |     await expect(replayLinks.first()).toBeVisible()
  137 |     expect(rejected).toEqual([])
  138 |   })
  139 | 
  140 |   test('P0-UI-009 世界杯：Match Center/Schedule/Groups/Bracket 表面', async ({ page }) => {
  141 |     const rejected = await guardP0(page, runtime)
  142 |     await page.goto(new URL('/worldcup-2026', runtime.baseUrl).toString(), { waitUntil: 'domcontentloaded' })
  143 |     await expect(page.getByText(/World Cup 2026|FIFA World Cup/i).first()).toBeVisible()
  144 |     const bodyText = await page.locator('body').innerText()
  145 |     expect(/Match Center|Schedule|Groups|Bracket/i.test(bodyText)).toBe(true)
  146 |     expect(rejected).toEqual([])
  147 |   })
  148 | 
  149 |   test('P0-UI-010 首页加载性能：15s 内完成', async ({ page }) => {
  150 |     const rejected = await guardP0(page, runtime)
  151 |     const startedAt = Date.now()
  152 |     await page.goto(runtime.baseUrl.toString(), { waitUntil: 'load' })
  153 |     expect(Date.now() - startedAt).toBeLessThan(15_000)
  154 |     expect(rejected).toEqual([])
  155 |   })
  156 | })
  157 | 
```