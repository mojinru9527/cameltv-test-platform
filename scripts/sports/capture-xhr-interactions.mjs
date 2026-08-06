#!/usr/bin/env node
/**
 * 体育平台生产 XHR 交互触发式采集（Batch 110，C103-5 补充）。
 *
 * 针对 SSR 站点 XHR 稀少的问题：按路由执行真实用户交互
 * （Tab 切换 / 搜索输入 / 翻页 / 详情点击），捕获同源 API 请求/响应。
 * 全部为只读操作（不登录、不支付、不写业务数据；仅触发查询类请求）。
 *
 * 运行: node scripts/sports/capture-xhr-interactions.mjs
 * 环境: PROD_BASE_URL / OUT_DIR / MAX_SAMPLES_PER_PATH
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
const OUT_DIR = path.resolve(process.env.OUT_DIR || path.join(REPO_ROOT, "test-platform-v2/work-logs/evidence/batch-110/xhr-samples"));
const API_HOSTS = ["api.cameltv.live", "api.cameltv.to"];
const MAX_RESPONSE_BYTES = 400 * 1024;
const MAX_SAMPLES_PER_PATH = Number(process.env.MAX_SAMPLES_PER_PATH || 4);

function apiKey(method, url, postData) {
  return crypto.createHash("sha1").update(`${method}|${url}|${postData || ""}`).digest("hex").slice(0, 12);
}

async function capture(page, samples, seen, label, fn) {
  const refs = [];
  const onReq = (req) => {
    const u = new URL(req.url());
    if (!API_HOSTS.includes(u.hostname)) return;
    if (!/json|text|x-www-form-urlencoded/i.test(req.headers()["content-type"] || "")) return;
    const key = apiKey(req.method(), req.url(), req.postData() || "");
    if (seen.has(key)) return;
    seen.add(key);
    refs.push({
      method: req.method(), url: req.url(), host: u.hostname,
      path: u.pathname + u.search,
      post_data: (req.postData() || "").slice(0, 6000),
      page_label: label, ts: Date.now(),
    });
  };
  const onRes = async (res) => {
    const u = new URL(res.url());
    if (!API_HOSTS.includes(u.hostname)) return;
    if (!/json/i.test(res.headers()["content-type"] || "")) return;
    const key = apiKey(res.request().method(), res.url(), res.request().postData() || "");
    const sample = refs.find((s) => apiKey(s.method, s.url, s.post_data) === key);
    if (!sample) return;
    try {
      const buf = await res.body();
      if (buf.length <= MAX_RESPONSE_BYTES) {
        sample.status = res.status();
        sample.response = buf.toString("utf-8").slice(0, 250000);
      } else {
        sample.status = res.status();
        sample.response = `[too-large:${buf.length}]`;
      }
    } catch {
      sample.status = res.status();
      sample.response = "[body-unavailable]";
    }
  };
  page.on("request", onReq);
  page.on("response", onRes);
  try {
    await page.goto(BASE + fn.url, { waitUntil: "domcontentloaded", timeout: 45000 });
    await page.waitForTimeout(2500);
    if (fn.actions) {
      for (const act of fn.actions) {
        await act(page);
        await page.waitForTimeout(1800);
      }
    }
  } catch (e) {
    console.log(`[warn] ${label}: ${e.message}`);
  } finally {
    page.removeListener("request", onReq);
    page.removeListener("response", onRes);
  }
  return refs;
}

async function clickByText(page, text, max = 3) {
  const clicked = await page.getByRole("button", { name: text, exact: false }).first().click({ timeout: 4000 }).then(() => true).catch(() => false);
  if (clicked) return true;
  return page.getByText(text, { exact: false }).first().click({ timeout: 4000 }).then(() => true).catch(() => false);
}

async function fillSearch(page) {
  const input = page.locator("input[type='text'], input[type='search'], input[placeholder*='search' i]").first();
  await input.fill("Real Madrid", { timeout: 4000 }).catch(() => {});
  await page.keyboard.press("Enter").catch(() => {});
}

const FLOWS = [
  {
    label: "home_tabs",
    url: "/",
    actions: [
      (p) => clickByText(p, "Favorites"),
      (p) => clickByText(p, "Competitions"),
      (p) => clickByText(p, "Match Replays"),
    ],
  },
  {
    label: "news_list_pagination",
    url: "/q/news",
    actions: [
      (p) => clickByText(p, "Load more"),
      (p) => clickByText(p, "Next"),
      (p) => p.mouse.wheel(0, 3000),
    ],
  },
  {
    label: "search_real_madrid",
    url: "/search",
    actions: [fillSearch],
  },
  {
    label: "match_detail_tabs",
    url: "/football/as-monaco-vs-getafe/n54qllhn0vwjqvy",
    actions: [
      (p) => clickByText(p, "Stats"),
      (p) => clickByText(p, "Lineups"),
      (p) => clickByText(p, "H2H"),
      (p) => clickByText(p, "Odds"),
      (p) => clickByText(p, "Prediction"),
      (p) => clickByText(p, "Picks"),
      (p) => clickByText(p, "Schedule"),
    ],
  },
  {
    label: "league_tabs",
    url: "/r/league/UEFA%20Europa%20League",
    actions: [
      (p) => clickByText(p, "Standings"),
      (p) => clickByText(p, "Schedule"),
      (p) => clickByText(p, "Top Scorers"),
    ],
  },
  {
    label: "team_tabs",
    url: "/team/Petro%20Atletico%20de%20Luanda/k82rekhv69drepz",
    actions: [
      (p) => clickByText(p, "Schedule"),
      (p) => clickByText(p, "Squad"),
      (p) => clickByText(p, "Statistics"),
    ],
  },
  {
    label: "replay_detail",
    url: "/match-replay/107123464706493798",
    actions: [
      (p) => p.mouse.wheel(0, 2000),
      (p) => clickByText(p, "More"),
    ],
  },
  {
    label: "worldcup_tabs",
    url: "/worldcup-2026",
    actions: [
      (p) => clickByText(p, "Match Center"),
      (p) => clickByText(p, "Schedule"),
      (p) => clickByText(p, "Groups"),
      (p) => clickByText(p, "Bracket"),
    ],
  },
  {
    label: "my_page",
    url: "/my",
    actions: [
      (p) => p.mouse.wheel(0, 2500),
      (p) => clickByText(p, "Login"),
    ],
  },
];

async function main() {
  fs.mkdirSync(OUT_DIR, { recursive: true });
  const browser = await playwright.chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, locale: "en-US" });
  const samples = [];
  const seen = new Set();
  for (const f of FLOWS) {
    const got = await capture(page, samples, seen, f.label, f);
    samples.push(...got);
    console.log(`[flow] ${f.label} xhr=${got.length}`);
  }
  await browser.close();

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
  const out = path.join(OUT_DIR, "xhr-samples-interactions.json");
  fs.writeFileSync(out, JSON.stringify({ base: BASE, captured_at: new Date().toISOString(), flows: FLOWS.length, samples: deduped }, null, 2), "utf-8");
  console.log("interaction xhr samples:", deduped.length, "saved:", path.relative(REPO_ROOT, out));
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
