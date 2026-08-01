/**
 * Redacted API traffic capture for UI automation.
 *
 * Captures are intentionally safe-by-default: credentials and session data are
 * removed from URLs, query parameters, headers, request bodies, and response
 * bodies before any entry is retained in memory or written to disk.
 */
import type { Page, Request, Response } from '@playwright/test'
import { promises as fs } from 'node:fs'
import path from 'node:path'

const REDACTED = '[REDACTED]'

interface CapturedEntry {
  source: 'ui-capture'
  session_id: string
  timestamp: string
  method: string
  url: string
  path: string
  query: Record<string, string>
  body: unknown
  headers: Record<string, unknown>
  status: number
  response_body?: unknown
}

let captured: CapturedEntry[] = []
let sessionId = ''
let pendingResponseCaptures = new Set<Promise<void>>()

function isSensitiveKey(key: string): boolean {
  const normalized = key.toLowerCase().replace(/[^a-z0-9]/g, '')
  return [
    'authorization',
    'cookie',
    'credential',
    'password',
    'passwd',
    'pwd',
    'secret',
    'apikey',
    'token',
    'session',
    'jwt',
  ].some((sensitiveName) => normalized.includes(sensitiveName))
}

function redactStructuredValue(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(redactStructuredValue)
  if (value && typeof value === 'object') {
    return Object.fromEntries(
      Object.entries(value).map(([key, nestedValue]) => [
        key,
        isSensitiveKey(key) ? REDACTED : redactStructuredValue(nestedValue),
      ]),
    )
  }
  return value
}

function redactPayload(value: unknown): unknown {
  if (typeof value !== 'string') return redactStructuredValue(value)
  const trimmed = value.trim()
  if (!trimmed) return value
  try {
    return redactStructuredValue(JSON.parse(trimmed))
  } catch {
    // An unstructured body cannot be proven safe. Preserve its existence, not
    // its contents.
    return REDACTED
  }
}

function redactUrl(rawUrl: string): string {
  try {
    const parsed = new URL(rawUrl)
    if (parsed.username) parsed.username = REDACTED
    if (parsed.password) parsed.password = REDACTED
    const pathSegments = parsed.pathname.split('/')
    for (let index = 0; index < pathSegments.length - 1; index += 1) {
      let segment = pathSegments[index]
      try {
        segment = decodeURIComponent(segment)
      } catch {
        // Keep the encoded segment; sensitive-key matching remains safe.
      }
      if (isSensitiveKey(segment) && pathSegments[index + 1]) {
        pathSegments[index + 1] = encodeURIComponent(REDACTED)
      }
    }
    parsed.pathname = pathSegments.join('/')
    for (const key of [...parsed.searchParams.keys()]) {
      if (isSensitiveKey(key)) parsed.searchParams.set(key, REDACTED)
    }
    return parsed.toString()
  } catch {
    return REDACTED
  }
}

function redactHeaders(headers: Record<string, string>): Record<string, unknown> {
  return Object.fromEntries(
    Object.entries(headers).map(([key, value]) => [
      key,
      isSensitiveKey(key) ? REDACTED : value,
    ]),
  )
}

function readRequestBody(request: Request): unknown {
  try {
    const jsonBody = request.postDataJSON()
    if (jsonBody !== null && jsonBody !== undefined) return redactStructuredValue(jsonBody)
  } catch {
    // Non-JSON request bodies fall back to the safe raw-body policy below.
  }
  return redactPayload(request.postData())
}

function resetCaptureState(nextSessionId = ''): void {
  captured = []
  pendingResponseCaptures = new Set()
  sessionId = nextSessionId
}

/** Initialize an isolated capture session and discard any prior in-memory data. */
export function initTrafficCapture(session: string): void {
  resetCaptureState(session)
}

/** Attach redacting request and response observers to a Playwright page. */
export function attachTrafficCapture(page: Page): void {
  page.on('request', (request: Request) => {
    const rawUrl = request.url()
    if (!rawUrl.includes('/api/') && !rawUrl.includes('/graphql')) return

    const safeUrl = redactUrl(rawUrl)
    if (safeUrl === REDACTED) return
    const parsed = new URL(safeUrl)
    const query = Object.fromEntries(parsed.searchParams.entries())

    captured.push({
      source: 'ui-capture',
      session_id: sessionId,
      timestamp: new Date().toISOString(),
      method: request.method(),
      url: safeUrl,
      path: parsed.pathname,
      query,
      body: readRequestBody(request),
      headers: redactHeaders(request.headers()),
      status: 0,
    })
  })

  page.on('response', (response: Response) => {
    const safeUrl = redactUrl(response.request().url())
    const entry = [...captured]
      .reverse()
      .find((candidate) => candidate.url === safeUrl && candidate.status === 0)
    if (!entry) return
    entry.status = response.status()

    const pending = (async () => {
      try {
        entry.response_body = redactStructuredValue(await response.json())
      } catch {
        try {
          entry.response_body = redactPayload(await response.text())
        } catch {
          // A missing/unreadable response body is valid capture metadata.
        }
      }
    })()
    pendingResponseCaptures.add(pending)
    void pending.finally(() => pendingResponseCaptures.delete(pending))
  })
}

/** Wait for response capture, write one JSONL artifact, then clear all state. */
export async function flushTrafficCapture(): Promise<void> {
  await Promise.allSettled([...pendingResponseCaptures])

  const entries = captured
  const completedSessionId = sessionId
  resetCaptureState()
  if (entries.length === 0) {
    return
  }

  const outDir = process.env.CAPTURE_OUTPUT_DIR || path.resolve(__dirname, '..', 'captured')
  await fs.mkdir(outDir, { recursive: true })

  const safeSessionId = completedSessionId.replace(/[^a-zA-Z0-9_-]/g, '-') || 'capture'
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-')
  const outFile = path.join(outDir, `${safeSessionId}-${timestamp}.jsonl`)
  const lines = entries.map((entry) => JSON.stringify(entry)).join('\n')
  await fs.writeFile(outFile, lines, 'utf8')
}
