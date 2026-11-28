const { chromium } = require('playwright');
const TEST_USERNAME = process.env.AIQE_TEST_USERNAME;
const TEST_PASSWORD = process.env.AIQE_TEST_PASSWORD;
if (!TEST_USERNAME || !TEST_PASSWORD) {
  console.error('AIQE_TEST_USERNAME / AIQE_TEST_PASSWORD are required');
  process.exit(2);
}

(async () => {
  const browser = await chromium.launch({ headless: false, slowMo: 80 });
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });

  const errors = [];
  page.on('console', (msg) => {
    if (msg.type() === 'error') errors.push('[CONSOLE] ' + msg.text());
  });
  page.on('pageerror', (err) => errors.push('[PAGE] ' + err.message));

  await page.goto('http://localhost:5173/login', { waitUntil: 'networkidle' });
  await page.fill('#username', TEST_USERNAME);
  await page.fill('#password', TEST_PASSWORD);
  await page.click('button[type="submit"]');
  await page.waitForURL((url) => !url.toString().includes('/login'), { timeout: 5000 });
  await page.waitForTimeout(2000);

  // Check each page
  for (const [path, label] of [
    ['/requirement', 'REQUIREMENTS'],
    ['/testcase', 'TEST CASES'],
    ['/integration', 'INTEGRATION'],
    ['/release-bundles', 'RELEASE BUNDLES'],
  ]) {
    errors.length = 0;
    await page.goto('http://localhost:5173' + path, { waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);
    console.log(`\n=== ${label} (${path}) ===`);
    console.log('URL:', page.url());
    if (errors.length > 0) {
      console.log('ERRORS:', errors.slice(0, 5).join('\n  '));
    }
    // Dump all button text on the page
    const btns = await page.$$('button');
    const btnTexts = [];
    for (const b of btns) {
      const t = await b.innerText().catch(() => '');
      if (t && t.length < 50) btnTexts.push(t);
    }
    console.log('Buttons:', JSON.stringify(btnTexts.slice(0, 30)));
  }

  await browser.close();
})();
