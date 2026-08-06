#!/usr/bin/env node
/**
 * 体育平台生产 XHR 真实样本定向采集（Batch 110，C103-5）。
 *
 * 复用 walkthrough v2 的页面清单，重新访问每个页面并触发交互
 * （滚动到底触发懒加载、点击 Load more/分页按钮），捕获同源 API
 * 请求/响应（JSON），合并去重后输出 ≥20 核心接口真实业务样本。
 *
 * 运行: node scripts/sports/capture-xhr-samples.mjs
 * 环境: PROD_BASE_URL / PAGES_JSON / OUT_DIR / MAX_SAMPLES_PER_PATH
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
const BASE = process.env.PROD_BASE_URL || "https://www.camel1.tv";
const WALK_DIR = path.resolve(process.env.WALK_DIR || path.join(REPO_ROOT, "test-platform-v2/work-logs/evidence/batch-110/production-walkthrough-v2"));
const OUT_DIR = path.resolve(process.env.OUT_DIR || path.join(REPO_ROOT, "test-platform-v2/work-logs/evidence/batch-110/xhr-samples"));
const API_HOSTS = ["api.cameltv.live", "api.cameltv.to", "sensors.cameltv.live"];
const MAX_RESPONSE_BYTES = 300 * 1024;
const MAX_SAMPLES_PER_PATH = Number(process.env.MAX_SAMPLES_PER_PATH || 3);
const SCROLL_STEPS = Number(process.env.SCROLL_STEPS || 3);

function apiKey(method, url, postData) {
  return crypto.createHash("sha1").update(`${method}|${url}|${postData || ""}`).digest("hex").slice(0, 12);
}

async function captureOnPage(page, samples, seen, label) {
  const sampleRef = [];
  const handlerReq = (req) => {
    const u = new URL(req.url());
    if (!API_HOSTS.includes(u.hostname)) return;
    if (!/json|text|x-www-form-urlencoded/i.test(req.headers()["content-type"] || "")) return;
    const key = apiKey(req.method(), req.url(), req.postData() || "");
    if (seen.has(key)) return;
    seen.add(key);
    sampleRef.push({
      method: req.method(),
      url: req.url(),
      host: u.hostname,
      path: u.pathname + u.search,
      post_data: (req.postData() || "").slice(0, 6000),
      page_label: label,
      ts: Date.now(),
    });
  };
  const handlerRes = async (res) => {
    const u = new URL(res.url());
    if (!API_HOSTS.includes(u.hostname)) return;
    if (!/json/i.test(res.headers()["content-type"] || "")) return;
    const key = apiKey(res.request().method(), res.url(), res.request().postData() || "");
    const sample = sampleRef.find((s) => apiKey(s.method, s.url, s.post_data) === key);
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
  };
  page.on("request", handlerReq);
  page.on("response", handlerRes);
  try {
    await page.goto(label.url || label, { waitUntil: "domcontentloaded", timeout: 45000 });
    await page.waitForTimeout(2000);
    // 滚动触发懒加载
    for (let i = 0; i < SCROLL_STEPS; i++) {
      await page.evaluate(() => window.scrollBy(0, window.innerHeight * 1.2));
      await page.waitForTimeout(900);
    }
    // 点击加载更多/分页按钮（只读交互）
    const clicked = await page.evaluate(() => {
      const btns = Array.from(document.querySelectorAll("button, a[role='button']"));
      const targets = btns.filter((b) => {
        const t = (b.innerText || b.textContent || "").trim().toLowerCase();
        return /load ?more|next|show more|view all|加载更多|下一页|更多/.test(t) && t.length < 30;
      }).slice(0, 3);
      let n = 0;
      for (const b of targets) {
        try { b.click(); n += 1; } catch { /* 忽略受保护元素 */ }
      }
      return n;
    });
    await page.waitForTimeout(2500);
    if (clicked) console.log(`[${label.label}] clicked load-more/pagination: ${clicked}`);
  } catch (e) {
    console.log(`[warn] ${label.label}: ${e.message}`);
  } finally {
    page.removeListener("request", handlerReq);
    page.removeListener("response", handlerRes);
  }
  return sampleRef;
}

async function main() {
  fs.mkdirSync(OUT_DIR, { recursive: true });
  let pages;
  const pagesJson = path.join(WALK_DIR, "production-pages.json");
  if (fs.existsSync(pagesJson)) {
    pages = JSON.parse(fs.readFileSync(pagesJson, "utf-8"));
  } else {
    pages = [{ url: BASE, label: "home" }];
  }
  const targets = pages
    .map((p) => ({ url: p.url || p, label: p.label || String(p) }))
    .slice(0, 30);

  const browser = await playwright.chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, locale: "en-US" });
  const samples = [];
  const seen = new Set();
  for (const t of targets) {
    const got = await captureOnPage(page, samples, seen, t);
    samples.push(...got);
    console.log(`[page] ${t.label} xhr=${got.length}`);
  }
  await browser.close();

  // 去重：按 host+path 保留最多 MAX_SAMPLES_PER_PATH 个不同样本
  const byPath = new Map();
  for (const s of samples) {
    const k = s.host + s.path.split("?")[0];
    const arr = byPath.get(k) || [];
    arr.push(s);
    byPath.set(k, arr);
  }
  const deduped = [];
  for (const arr of byPath.values()) {
    deduped.push(...arr.slice(0, MAX_SAMPLES_PER_PATH));
  }
  deduped.sort((a, b) => (a.host + a.path).localeCompare(b.host + b.path));

  const out = path.join(OUT_DIR, "xhr-samples-merged.json");
  fs.writeFileSync(out, JSON.stringify({ base: BASE, captured_at: new Date().toISOString(), pages_visited: targets.length, samples: deduped }, null, 2), "utf-8");
  console.log("merged xhr samples:", deduped.length, "saved:", path.relative(REPO_ROOT, out));
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
