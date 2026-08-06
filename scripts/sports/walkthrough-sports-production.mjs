#!/usr/bin/env node
/**
 * 体育平台生产页面功能模块勘察（Batch 102）。
 *
 * 真实浏览器访问 www.camel1.tv：首页 → 收集导航/链接 → 访问核心页面
 * 提取标题/导航/正文文本/按钮 → 截图 → 输出 JSON 清单。
 *
 * 运行: node scripts/sports/walkthrough-sports-production.mjs
 * 依赖: playwright（全局或 NODE_PATH 指向全局 node_modules）
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
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(__dirname, "../..");
const OUT_DIR = path.join(REPO_ROOT, "test-platform-v2/work-logs/evidence/batch-102/production-walkthrough");
const BASE = process.env.PROD_BASE_URL || "https://www.camel1.tv";
const MAX_PAGES = Number(process.env.MAX_PAGES || 16);

const ROUTE_HINTS = [
  { key: "match", re: /match|赛事|schedule|fixture/i },
  { key: "live", re: /live|直播|stream/i },
  { key: "news", re: /news|资讯|article/i },
  { key: "ugc", re: /ugc/i },
  { key: "search", re: /search|搜索/i },
  { key: "mine", re: /mine|user|my|我的|profile/i },
  { key: "team", re: /team|球队/i },
  { key: "player", re: /player|球员/i },
  { key: "league", re: /league|联赛/i },
  { key: "rank", re: /rank|榜单|榜/i },
  { key: "predict", re: /predict|预测/i },
  { key: "picks", re: /picks/i },
];

const EXPLICIT_PATTERNS = [
  { key: "match_page", re: /^\/football\/.+\/.+$/ },
  { key: "live_page", re: /\/football\/.+\/live\// },
  { key: "replay", re: /^\/match-replay/ },
  { key: "worldcup", re: /worldcup/i },
];

function normalizeHref(href, baseUrl) {
  try {
    const u = new URL(href, baseUrl);
    if (u.origin !== new URL(BASE).origin) return null;
    return u.pathname + u.search;
  } catch {
    return null;
  }
}

async function collectPage(page, url, label) {
  await page.goto(url, { waitUntil: "domcontentloaded", timeout: 45000 });
  await page.waitForTimeout(2500);
  const data = await page.evaluate(() => {
    const txt = (sel) =>
      Array.from(document.querySelectorAll(sel))
        .map((el) => (el.innerText || el.textContent || "").trim())
        .filter(Boolean)
        .slice(0, 20);
    const links = Array.from(document.querySelectorAll("a[href]"))
      .map((a) => ({ text: (a.innerText || a.title || "").trim(), href: a.getAttribute("href") || "" }))
      .filter((l) => l.text && l.href)
      .slice(0, 120);
    const buttons = Array.from(document.querySelectorAll("button, [role='button'], [data-testid]"))
      .map((b) => (b.innerText || b.getAttribute("aria-label") || b.getAttribute("data-testid") || "").trim())
      .filter(Boolean)
      .slice(0, 60);
    const mainText = (document.querySelector("main") || document.body).innerText
      .replace(/\s+/g, " ")
      .slice(0, 1200);
    return {
      title: document.title,
      headings: txt("h1,h2,h3"),
      navText: txt("nav, header, [role='navigation']"),
      mainText,
      links,
      buttons,
      url: location.href,
    };
  });
  data.label = label;
  const shot = path.join(OUT_DIR, `${label.replace(/[^\w\u4e00-\u9fa5-]/g, "_")}.png`);
  await page.screenshot({ path: shot, fullPage: false });
  data.screenshot = path.relative(REPO_ROOT, shot);
  return data;
}

async function main() {
  fs.mkdirSync(OUT_DIR, { recursive: true });
  const browser = await playwright.chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, locale: "zh-CN" });

  const inventory = [];
  const visited = new Set();
  const home = await collectPage(page, BASE, "home");
  inventory.push(home);
  visited.add(new URL(home.url).pathname);

  // 按导航提示匹配链接
  const candidates = [];
  for (const link of home.links) {
    const href = normalizeHref(link.href, home.url);
    if (!href || visited.has(href.split("?")[0])) continue;
    for (const hint of ROUTE_HINTS) {
      if (hint.re.test(link.text + " " + href)) {
        candidates.push({ href, label: `${hint.key}_${link.text.slice(0, 16) || href}`, hint: hint.key });
        break;
      }
    }
  }
  // 显式路由模式（赛事详情/直播间/回放/世界杯页）
  for (const link of home.links) {
    const href = normalizeHref(link.href, home.url);
    if (!href || visited.has(href.split("?")[0])) continue;
    for (const pat of EXPLICIT_PATTERNS) {
      if (pat.re.test(href.split("?")[0])) {
        candidates.push({ href, label: `${pat.key}_${link.text.slice(0, 16) || href}`, hint: pat.key });
        break;
      }
    }
  }
  const seen = new Set();
  const picks = [];
  for (const c of candidates) {
    const p = c.href.split("?")[0];
    if (!seen.has(c.hint)) {
      seen.add(c.hint);
      picks.push(c);
    }
  }
  for (const p of picks.slice(0, MAX_PAGES)) {
    const full = new URL(p.href, home.url).toString();
    try {
      const data = await collectPage(page, full, p.label);
      inventory.push(data);
      visited.add(new URL(full).pathname);
    } catch (e) {
      console.log("[warn] skip", p.href, e.message);
    }
  }

  await browser.close();
  const outFile = path.join(OUT_DIR, "production-pages.json");
  fs.writeFileSync(outFile, JSON.stringify(inventory, null, 2), "utf-8");
  console.log("pages:", inventory.length, "saved:", path.relative(REPO_ROOT, outFile));
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
