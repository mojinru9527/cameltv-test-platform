// B173-28: 验证用例内容质量问题（数字被拆分 "2、0" 样式）的分布与源头
const fs = require('fs');
const { chromium } = require('playwright');
const BASE = 'https://cameltv-test-platform1.vercel.app';
const STATE = 'F:/CamelTv-batch173-review/_review_tools/b173/prod-storage-state.json';
const EVID = 'F:/CamelTv-batch173-review/_review_tools/b173/evidence/';

(async () => {
  fs.mkdirSync(EVID, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ storageState: STATE, viewport: { width: 1600, height: 900 } });
  const page = await context.newPage();
  const note = (m) => console.log('###', m);
  await page.goto(BASE + '/testcase', { waitUntil: 'networkidle', timeout: 60000 });
  await page.waitForTimeout(1500);

  // 用 API 搜索包含 "2、0" 或 "1、0" 特征的用例
  const probe = async (kw) => {
    const r = await page.evaluate(async (k) => {
      const resp = await fetch('/api/v1/test-cases?page=1&page_size=5&keyword=' + encodeURIComponent(k), { headers: { 'X-Project-Id': '1' } });
      const b = await resp.json().catch(() => null);
      return { status: resp.status, total: b && b.data ? b.data.total : null };
    }, kw);
    note(`搜索"${kw}": total=${r.total}`);
    return r;
  };
  await probe('2、0');
  await probe('latestVersion');
  await probe('上限 2、');
  await probe('假设上限');

  // 拉取一条受影响的用例详情，确认存储格式
  const detail = await page.evaluate(async () => {
    const resp = await fetch('/api/v1/test-cases?page=1&page_size=1&keyword=' + encodeURIComponent('设置订阅金额为超大值'), { headers: { 'X-Project-Id': '1' } });
    const b = await resp.json();
    const item = b.data.items[0];
    return { id: item.id, title: item.title, preconditions: item.preconditions, steps: item.steps };
  });
  note('受影响用例详情: ' + JSON.stringify(detail).slice(0, 700));
  fs.writeFileSync(EVID + '28-quality-case.json', JSON.stringify(detail, null, 2));

  // 再抽查另一条
  const detail2 = await page.evaluate(async () => {
    const resp = await fetch('/api/v1/test-cases?page=1&page_size=1&keyword=' + encodeURIComponent('版本接口返回'), { headers: { 'X-Project-Id': '1' } });
    const b = await resp.json();
    const item = b.data.items[0];
    return { id: item.id, title: item.title, preconditions: item.preconditions, steps: item.steps };
  });
  note('另一条: ' + JSON.stringify(detail2).slice(0, 600));

  await browser.close();
})();
