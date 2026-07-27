/**
 * 登录辅助 — 使用 midscene.js 自然语言指令完成登录。
 *
 * midscene.js 原理：给自然语言指令 → 把页面截图+DOM 发给多模态大模型判断操作。
 * 模型后端可配置（.env MIDSCENE_MODEL_BACKEND），默认通义千问-VL。
 */
import { Page } from '@playwright/test';
import { ai, aiBoolean, aiAction } from '@midscene/web';

/**
 * 使用自然语言完成登录流程。
 * 依赖环境变量 CAMELTV_USERNAME / CAMELTV_PASSWORD。
 */
export async function login(page: Page): Promise<void> {
  const username = process.env.CAMELTV_USERNAME || 'qa_test';
  const password = process.env.CAMELTV_PASSWORD || '';

  await page.goto('/');

  // 检查是否已登录
  const isLoggedIn = await aiBoolean('Is the user already logged in? Look for a profile icon or user menu.');
  if (isLoggedIn) {
    console.log('[auth] Already logged in, skipping login flow.');
    return;
  }

  // 点击登录入口
  await aiAction('click the login/sign-in button');
  await page.waitForTimeout(1500);

  // 填写凭据
  await aiAction(`type "${username}" in the username/email input field`);
  await aiAction(`type "${password}" in the password input field`);
  await aiAction('click the login submit button');

  await page.waitForTimeout(3000);

  // 验证登录成功
  const loginSuccess = await aiBoolean('Did the login succeed? Is there a profile icon or user greeting visible?');
  if (!loginSuccess) {
    throw new Error('[auth] Login failed — check credentials or page layout changes.');
  }
  console.log('[auth] Login succeeded.');
}

/**
 * 登出。
 */
export async function logout(page: Page): Promise<void> {
  await aiAction('click the profile/user menu');
  await page.waitForTimeout(500);
  await aiAction('click logout/sign-out');
  await page.waitForTimeout(1500);
  console.log('[auth] Logged out.');
}
