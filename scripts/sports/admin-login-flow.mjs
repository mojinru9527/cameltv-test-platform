#!/usr/bin/env node
/**
 * 运营后台（admcamel.camel1.tv）只读登录流程（Batch 110）。
 *
 * 登录链路：用户名 + 图形验证码（vision 识别）→ 验证 → 短信验证码（用户提供）→ 登录。
 * 本脚本与外部协调通过两个应答文件：
 *   CAPTCHA_ANSWER_FILE：识图结果（agent 写入）
 *   SMS_ANSWER_FILE：短信验证码（用户提供后 agent 写入）
 * 状态输出到 STATE_FILE（agent 可读，决定下一步）。
 *
 * 运行: node scripts/sports/admin-login-flow.mjs
 */
import { createRequire } from "module";
const require = createRequire(import.meta.url);
let playwright;
try {
  playwright = require("playwright");
} catch {
  playwright = require("C:/Users/26029/AppData/Roaming/npm/node_modules/playwright");
}

import fs from "node:fs";
import path from "node:path";
import os from "node:os";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(__dirname, "../..");
const EVIDENCE = path.join(REPO_ROOT, "test-platform-v2/work-logs/evidence/batch-110/admin-walkthrough");
const TMP = os.tmpdir();
const STATE = process.env.STATE_FILE || path.join(TMP, "admin-login-state.json");
const CAPTCHA_ANSWER = process.env.CAPTCHA_ANSWER_FILE || path.join(TMP, "admin-captcha-answer.txt");
const SMS_ANSWER = process.env.SMS_ANSWER_FILE || path.join(TMP, "admin-sms-answer.txt");
const USERDATA = process.env.USERDATA_DIR || path.join(TMP, "admin-pw-profile");
const USER = process.env.ADMIN_USER || "18476944071";

function setState(s) {
  fs.writeFileSync(STATE, JSON.stringify({ ...s, ts: new Date().toISOString() }, null, 2));
  console.log("[state]", JSON.stringify(s));
}

function waitForFile(file, timeoutMs, label) {
  const start = Date.now();
  return new Promise((resolve) => {
    const iv = setInterval(() => {
      if (fs.existsSync(file)) {
        const v = fs.readFileSync(file, "utf-8").trim();
        if (v) {
          clearInterval(iv);
          resolve(v);
          return;
        }
      }
      if (Date.now() - start > timeoutMs) {
        clearInterval(iv);
        resolve(null);
      }
    }, 1500);
  });
}

async function main() {
  fs.mkdirSync(EVIDENCE, { recursive: true });
  fs.mkdirSync(USERDATA, { recursive: true });
  const browser = await playwright.chromium.launchPersistentContext(USERDATA, {
    headless: true,
    viewport: { width: 1440, height: 900 },
    args: ["--disable-blink-features=AutomationControlled"],
  });
  const page = browser.pages()[0] || (await browser.newPage());
  const apiHits = [];
  page.on("request", (req) => {
    const u = new URL(req.url());
    if (/admcamel|camel1\.tv/i.test(u.hostname) && /api|captcha|login|sms/i.test(u.pathname)) {
      apiHits.push({ method: req.method(), url: req.url().slice(0, 200), page: page.url().slice(0, 120) });
    }
  });

  setState({ step: "goto_login" });
  await page.goto("https://admcamel.camel1.tv/login", { waitUntil: "domcontentloaded", timeout: 60000 });
  await page.waitForTimeout(3500);

  // 抓图形验证码
  const captchaSrc = await page.locator("img[src*='captcha']").getAttribute("src").catch(() => "");
  if (captchaSrc) {
    const captchaUrl = new URL(captchaSrc, page.url()).toString();
    const r = await page.context().request.get(captchaUrl);
    const buf = await r.body();
    fs.writeFileSync(path.join(EVIDENCE, "captcha.png"), buf);
    setState({ step: "captcha_ready", captcha: captchaUrl.slice(0, 160), captcha_file: path.join(EVIDENCE, "captcha.png") });
  } else {
    setState({ step: "captcha_missing" });
  }

  const captchaTimeout = Number(process.env.CAPTCHA_TIMEOUT || 1800000);
  const smsTimeout = Number(process.env.SMS_TIMEOUT || 1800000);
  const captcha = await waitForFile(CAPTCHA_ANSWER, captchaTimeout, "captcha");
  if (!captcha) {
    setState({ step: "captcha_timeout" });
    await browser.close();
    return;
  }
  setState({ step: "filling_captcha" });
  await page.locator("#userCode").fill(USER);
  await page.locator("#imageVerifyCode").fill(captcha.trim());
  await page.locator("button:has-text('验证')").first().click().catch((e) => console.log("click err", e.message));
  await page.waitForTimeout(9000);
  await page.screenshot({ path: path.join(EVIDENCE, "02-after-verify.png") });

  const smsVisible = await page.locator("input[name='smsCode'], input[placeholder*='code' i]").last().isVisible().catch(() => false);
  const pageText = (await page.locator("body").innerText().catch(() => "")).replace(/\s+/g, " ").slice(0, 300);
  setState({ step: "sms_ready", sms_visible: smsVisible, page_text: pageText });

  const sms = await waitForFile(SMS_ANSWER, smsTimeout, "sms");
  if (!sms) {
    setState({ step: "sms_timeout" });
    await browser.close();
    return;
  }
  setState({ step: "filling_sms" });
  await page.locator("input[name='smsCode']").fill(sms.trim());
  const loginBtn = page.locator("button:has-text('登录'), button[type='submit'], button:has-text('Sign in'), button:has-text('Log in')").first();
  await loginBtn.click().catch(async () => {
    await page.keyboard.press("Enter");
  });
  await page.waitForTimeout(9000);
  await page.screenshot({ path: path.join(EVIDENCE, "03-after-login.png") });
  const url = page.url();
  const bodyText = (await page.locator("body").innerText().catch(() => "")).replace(/\s+/g, " ").slice(0, 800);
  setState({ step: "done", url, body_text: bodyText });
  fs.writeFileSync(path.join(EVIDENCE, "admin-login-result.json"), JSON.stringify({ url, bodyText, apiHits: apiHits.slice(0, 40) }, null, 2));
  console.log("[done] url:", url);
  console.log("[text]", bodyText.slice(0, 400));
  await browser.close();
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
