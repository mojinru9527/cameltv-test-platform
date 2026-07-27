/**
 * API 流量捕获 — Playwright request 拦截器。
 *
 * 在 UI 自动化运行时捕获所有 API 请求，序列化为 JSONL。
 * 每条记录标记 source: ui-capture，供 §4 API 测试引擎补充 swagger 未覆盖的接口。
 *
 * 输出路径: tests/api-testing/captured/<session-id>-<timestamp>.jsonl
 */
import { Page, Request, Response } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

interface CapturedEntry {
  source: 'ui-capture';
  session_id: string;
  timestamp: string;
  method: string;
  url: string;
  path: string;
  query: Record<string, string>;
  body: unknown;
  headers: Record<string, string>;
  status: number;
  response_body?: unknown;
}

const captured: CapturedEntry[] = [];
let sessionId: string = '';

/**
 * 初始化流量捕获。应在 test.beforeAll 中调用。
 */
export function initTrafficCapture(session: string): void {
  sessionId = session;
  console.log(`[traffic-capture] Session started: ${sessionId}`);
}

/**
 * 绑定 page 的 request/response 拦截器。
 * 放在 test.beforeEach 中调用。
 */
export function attachTrafficCapture(page: Page): void {
  page.on('request', (request: Request) => {
    // 只捕获 API 请求（过滤静态资源）
    const url = request.url();
    if (!url.includes('/api/') && !url.includes('/graphql')) {
      return;
    }

    const parsed = new URL(url);
    const query: Record<string, string> = {};
    parsed.searchParams.forEach((v, k) => { query[k] = v; });

    captured.push({
      source: 'ui-capture',
      session_id: sessionId,
      timestamp: new Date().toISOString(),
      method: request.method(),
      url,
      path: parsed.pathname,
      query,
      body: request.postDataJSON() || request.postData(),
      headers: request.headers(),
      status: 0, // to be filled on response
    });
  });

  page.on('response', (response: Response) => {
    // 回填状态码到最近匹配的请求
    const reqUrl = response.request().url();
    for (let i = captured.length - 1; i >= 0; i--) {
      if (captured[i].url === reqUrl && captured[i].status === 0) {
        captured[i].status = response.status();
        // 尝试读取 JSON body
        try {
          response.json().then((body) => {
            captured[i].response_body = body;
          }).catch(() => {});
        } catch {
          // ignore parse errors
        }
        break;
      }
    }
  });
}

/**
 * 将捕获的流量写入 JSONL 文件。
 * 放在 test.afterAll 中调用。
 */
export function flushTrafficCapture(): void {
  if (captured.length === 0) {
    console.log('[traffic-capture] No API traffic captured.');
    return;
  }

  const outDir = process.env.CAPTURE_OUTPUT_DIR || path.resolve(__dirname, '..', 'captured');
  if (!fs.existsSync(outDir)) {
    fs.mkdirSync(outDir, { recursive: true });
  }

  const ts = new Date().toISOString().replace(/[:.]/g, '-');
  const outFile = path.join(outDir, `${sessionId}-${ts}.jsonl`);
  const lines = captured.map((e) => JSON.stringify(e)).join('\n');
  fs.writeFileSync(outFile, lines, 'utf-8');

  console.log(`[traffic-capture] Flushed ${captured.length} API calls → ${outFile}`);
}
