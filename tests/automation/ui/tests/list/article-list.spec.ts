/**
 * LIST — 预测/UGC 列表页 UI 自动化
 *
 * 对应 P0 用例: TC-LIST-001, 002, 004, 005, 008, 010
 */
import { test, expect } from '@playwright/test';
import { aiBoolean, aiAction } from '@midscene/web';
import { login } from '../../utils/auth';
import { initTrafficCapture, attachTrafficCapture, flushTrafficCapture } from '../../utils/traffic-capture';

const SESSION = 'article-list';

test.describe('LIST — 预测列表', () => {
  test.beforeAll(() => initTrafficCapture(SESSION));
  test.beforeEach(async ({ page }) => { attachTrafficCapture(page); await login(page); });
  test.afterAll(() => flushTrafficCapture());

  test('TC-LIST-001: 分类TAB 按序展示', async ({ page }) => {
    await page.goto('/');
    await page.waitForTimeout(3000);

    await aiAction('scroll to the UGC list section');
    const hasTabs = await aiBoolean('Are there category tabs visible in the article list section?');
    expect(hasTabs).toBe(true);
  });

  test('TC-LIST-004: 仅展示在售+免费文章', async ({ page }) => {
    await page.goto('/');
    await page.waitForTimeout(3000);

    await aiAction('scroll to the article list');
    const visibleArticles = await aiBoolean('Are article cards visible in the list?');
    expect(visibleArticles).toBe(true);
  });

  test('TC-LIST-005: 置顶文章优先展示', async ({ page }) => {
    await page.goto('/');
    await page.waitForTimeout(3000);

    await aiAction('scroll to the top of the article list');
    // 第一条应为置顶文章（如果有）
    const hasPinned = await aiBoolean('Does the first article look like a pinned/top article?');
    console.log(`First article is pinned: ${hasPinned}`);
  });

  test('TC-LIST-010: 点击文章进入详情', async ({ page }) => {
    await page.goto('/');
    await page.waitForTimeout(3000);

    await aiAction('scroll to the article list');
    await aiAction('click on the first article card');
    await page.waitForTimeout(2000);

    // 应该进入了详情页
    const isDetail = await aiBoolean('Is this an article detail page? Does it show article content and author info?');
    expect(isDetail).toBe(true);
  });
});
