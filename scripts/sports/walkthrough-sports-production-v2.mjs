#!/usr/bin/env node
/**
 * 体育平台生产页面功能模块勘察 v2（Batch 110）。
 *
 * 在 batch-102 v1 基础上增强：
 *  1) BFS 两层级联发现路由（首页 → 全部导航/链接 → 子页链接），覆盖 /my 全子页/登录/搜索/
 *     联赛/球队/球员/回放/世界杯/赛事详情/直播间/资讯详情等；
 *  2) 页面访问时捕获同源 API（api.cameltv.live）XHR 请求与响应 → 真实业务样本；
 *  3) 每页截图（1440x900），供 vision 识图走查。
 *
 * 运行: node scripts/sports/walkthrough-sports-production-v2.mjs
 * 依赖: playwright（全局 C:/Users/26029/AppData/Roaming/npm/node_modules/playwright 或 NODE_PATH）
 * 环境: PROD_BASE_URL / MAX_PAGES / MAX_DEPTH / OUT_DIR
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
import crypto from "node:crypto";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(__dirname, "../..");
const OUT_DIR = path.resolve(process.env.OUT_DIR || path.join(REPO_ROOT, "test-platform-v2/work-logs/evidence/batch-110/production-walkthrough-v2"));
const BASE = process.env.PROD_BASE_URL || "https://www.camel1.tv";
const API_HOSTS = ["api.cameltv.live", "api.cameltv.to", "sensors.cameltv.live"];
const MAX_PAGES = Number(process.env.MAX_PAGES || 40);
const MAX_DEPTH = Number(process.env.MAX_DEPTH || 2);
const MAX_RESPONSE_BYTES = 300 * 1024;

const ROUTE_HINTS = [
  { key: "match", re: /match|赛事|schedule|fixture|赛程/i },
  { key: "live", re: /live|直播|stream|room/i },
  { key: "news", re: /news|资讯|article/i },
  { key: "ugc", re: /ugc|creator|创作/i },
  { key: "search", re: /search|搜索/i },
  { key: "mine", re: /mine|user|my|我的|profile/i },
  { key: "team", re: /team|球队/i },
  { key: "player", re: /player|球员/i },
  { key: "league", re: /league|联赛/i },
  { key: "rank", re: /rank|榜单|榜/i },
  { key: "predict", re: /predict|预测/i },
  { key: "picks", re: /picks/i },
  { key: "recharge", re: /recharge|pay|charge|recharge|充值/i },
  { key: "coin", re: /coin|camel.*coin|骆驼币|银钻|diamond/i },
  { key: "shop", re: /shop|mall|商城/i },
  { key: "favorite", re: /favorite|collect|收藏/i },
  { key: "faq", re: /faq|help|support|帮助/i },
  { key: "feedback", re: /feedback|意见|suggest/i },
  { key: "login", re: /login|signin|登录/i },
  { key: "register", re: /register|signup|注册/i },
  { key: "message", re: /message|notify|消息|通知/i },
  { key: "dress", re: /dress|decoration|avatar|勋章|装扮|头像框/i },
  { key: "creator", re: /creator|author|创作者|作者/i },
  { key: "setting", re: /setting|设置/i },
  { key: "vip", re: /vip|member|会员/i },
  { key: "gift", re: /gift|打赏|礼物/i },
];

const EXPLICIT_PATTERNS = [
  { key: "match_page", re: /^\/football\/.+\/.+$/ },
  { key: "live_page", re: /\/football\/.+\/live\// },
  { key: "replay", re: /^\/match-replay/ },
  { key: "worldcup", re: /worldcup/i },
  { key: "league_page", re: /^\/r\/league/i },
  { key: "team_page", re: /^\/team\//i },
  { key: "news_detail", re: /\/news\/detail\//i },
  { key: "my_page", re: /^\/my($|\/)/i },
];

function normalizeHref(href, baseUrl) {
  try {
    const u = new URL(href, baseUrl);
    if (u.origin !== new URL(BASE).origin) return null;
    const p = u.pathname + u.search;
    if (/\.(png|jpg|jpeg|gif|webp|svg|css|js|woff2?|mp4|m3u8)(\?|$)/i.test(p)) return null;
    return p;
  } catch {
    return null;
  }
}

function apiKey(method, url, postData) {
  return crypto.createHash("sha1").update(`${method}|${url}|${postData || ""}`).digest("hex").slice(0, 12);
}

async function collectPage(page, url, label, depth, xhrSamples, xhrSeen) {
  let data;
  try {
    await page.goto(url, { waitUntil: "domcontentloaded", timeout: 45000 });
    await page.waitForTimeout(2500);
  } catch (e) {
    return { label, url, error: e.message, depth };
  }
  data = await page.evaluate(() => {
    const txt = (sel) =>
      Array.from(document.querySelectorAll(sel))
        .map((el) => (el.innerText || el.textContent || "").trim())
        .filter(Boolean)
        .slice(0, 20);
    const links = Array.from(document.querySelectorAll("a[href]"))
      .map((a) => ({ text: (a.innerText || a.title || "").trim().slice(0, 60), href: a.getAttribute("href") || "" }))
      .filter((l) => l.text && l.href)
      .slice(0, 150);
    const buttons = Array.from(document.querySelectorAll("button, [role='button'], [data-testid]"))
      .map((b) => (b.innerText || b.getAttribute("aria-label") || b.getAttribute("data-testid") || "").trim())
      .filter(Boolean)
      .slice(0, 60);
    const mainText = (document.querySelector("main") || document.body).innerText.replace(/\s+/g, " ").slice(0, 1500);
    return {
      title: document.title,
      url: location.href,
      headings: txt("h1,h2,h3"),
      navText: txt("nav, header, [role='navigation']"),
      mainText,
      links,
      buttons,
    };
  });
  data.label = label;
  data.depth = depth;
  const shotName = `${label.replace(/[^\w\u4e00-\u9fa5-]/g, "_").slice(0, 80)}.png`;
  const shot = path.join(OUT_DIR, "screenshots", shotName);
  try {
    await page.screenshot({ path: shot, fullPage: false });
    data.screenshot = path.relative(REPO_ROOT, shot);
  } catch (e) {
    data.screenshotError = e.message;
  }
  return data;
}

async function main() {
  fs.mkdirSync(path.join(OUT_DIR, "screenshots"), { recursive: true });
  const browser = await playwright.chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, locale: "en-US" });
  const xhrSamples = [];
  const xhrSeen = new Set();
  const consoleErrors = [];

  page.on("console", (msg) => {
    if (msg.type() === "error") consoleErrors.push(msg.text().slice(0, 300));
  });
  page.on("request", (req) => {
    const u = new URL(req.url());
    if (!API_HOSTS.includes(u.hostname)) return;
    if (!/json|text|x-www-form-urlencoded/i.test(req.headers()["content-type"] || "")) return;
    const key = apiKey(req.method(), req.url(), req.postData() || "");
    if (xhrSeen.has(key)) return;
    xhrSeen.add(key);
    xhrSamples.push({
      method: req.method(),
      url: req.url(),
      host: u.hostname,
      path: u.pathname + u.search,
      post_data: (req.postData() || "").slice(0, 6000),
      page: page.url(),
      ts: Date.now(),
    });
  });
  page.on("response", async (res) => {
    const u = new URL(res.url());
    if (!API_HOSTS.includes(u.hostname)) return;
    const ct = res.headers()["content-type"] || "";
    if (!/json/i.test(ct)) return;
    const key = apiKey(res.request().method(), res.url(), res.request().postData() || "");
    const sample = xhrSamples.find((s) => apiKey(s.method, s.url, s.post_data) === key);
    if (!sample) return;
    try {
      const buf = await res.body();
      if (buf.length <= MAX_RESPONSE_BYTES) {
        sample.status = res.status();
        sample.response = buf.toString("utf-8").slice(0, 200000);
      } else {
        sample.status = res.status();
        sample.response = `[too-large:${buf.length}]`;
      }
    } catch {
      sample.status = res.status();
      sample.response = "[body-unavailable]";
    }
  });

  const inventory = [];
  const visited = new Set();
  const queue = [];

  const home = await collectPage(page, BASE, "home", 0, xhrSamples, xhrSeen);
  inventory.push(home);
  visited.add(new URL(home.url).pathname.replace(/\/$/, ""));
  queue.push({ url: home.url, depth: 1, links: home.links || [] });

  for (let qi = 0; qi < queue.length && inventory.length < MAX_PAGES; qi++) {
    const { url: pageUrl, depth, links } = queue[qi];
    if (depth > MAX_DEPTH) continue;
    const candidates = [];
    const seen = new Set();
    for (const link of links) {
      const href = normalizeHref(link.href, pageUrl);
      if (!href) continue;
      const p = href.split("?")[0].replace(/\/$/, "");
      if (visited.has(p) || seen.has(p)) continue;
      let matched = null;
      for (const hint of ROUTE_HINTS) {
        if (hint.re.test(link.text + " " + href)) { matched = hint.key; break; }
      }
      if (!matched) {
        for (const pat of EXPLICIT_PATTERNS) {
          if (pat.re.test(p)) { matched = pat.key; break; }
        }
      }
      if (!matched) continue;
      seen.add(p);
      candidates.push({ p, full: new URL(href, pageUrl).toString(), label: `${matched}_${link.text.slice(0, 12) || p}`, matched });
    }
    for (const c of candidates) {
      if (inventory.length >= MAX_PAGES) break;
      const data = await collectPage(page, c.full, c.label, depth, xhrSamples, xhrSeen);
      inventory.push(data);
      const p = new URL(c.full).pathname.replace(/\/$/, "");
      visited.add(p);
      if (depth < MAX_DEPTH && data.links) {
        queue.push({ url: c.full, depth: depth + 1, links: data.links });
      }
    }
  }

  await browser.close();

  // 去重 XHR：按 host+path 保留最多 3 个不同样本（翻页/参数变化）
  const deduped = [];
  const byPath = new Map();
  for (const s of xhrSamples) {
    const k = s.host + s.path.split("?")[0];
    const arr = byPath.get(k) || [];
    arr.push(s);
    byPath.set(k, arr);
  }
  for (const arr of byPath.values()) {
    deduped.push(...arr.slice(0, 3));
  }
  deduped.sort((a, b) => (a.host + a.path).localeCompare(b.host + b.path));

  const outPages = path.join(OUT_DIR, "production-pages.json");
  const outXhr = path.join(OUT_DIR, "xhr-samples.json");
  fs.writeFileSync(outPages, JSON.stringify(inventory, null, 2), "utf-8");
  fs.writeFileSync(outXhr, JSON.stringify({ base: BASE, captured_at: new Date().toISOString(), pages_visited: inventory.length, samples: deduped }, null, 2), "utf-8");
  const outConsole = path.join(OUT_DIR, "console-errors.json");
  fs.writeFileSync(outConsole, JSON.stringify(consoleErrors.slice(0, 50), null, 2), "utf-8");
  console.log("pages:", inventory.length, "xhr samples:", deduped.length, "console errors:", consoleErrors.length);
  console.log("saved:", path.relative(REPO_ROOT, outPages), path.relative(REPO_ROOT, outXhr), path.relative(REPO_ROOT, outConsole));
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
