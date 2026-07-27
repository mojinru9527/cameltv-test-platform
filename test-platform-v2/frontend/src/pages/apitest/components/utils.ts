/**
 * API 调试共享工具函数
 * 被 DebugTab、ApiDebugPanel 等组件复用
 */

/**
 * 安全解析 JSON，失败时返回 fallback
 * 处理 string/object 两种输入，防止 double-parse
 */
export function normalizeJson(raw: any, fallback: any): any {
  if (!raw) return fallback
  if (typeof raw !== 'string') return raw
  try { return JSON.parse(raw) } catch { return fallback }
}

/**
 * 生成默认断言规则 JSON 字符串
 * 状态码 2xx + 响应时间 < 5s
 */
export function defaultAssertions(): string {
  return JSON.stringify([
    { type: 'status_code', expected: 200, operator: 'gte' },
    { type: 'status_code', expected: 300, operator: 'lt' },
    { type: 'response_time', expected: 5000, operator: 'lt' },
  ], null, 2)
}

/**
 * 根据 OpenAPI schema properties 生成示例请求体 JSON 字符串
 * 用于 pre-fill endpoint 的 Body 编辑区
 */
export function buildSampleBody(properties: Record<string, any>): string {
  const obj: Record<string, any> = {}
  for (const [key, prop] of Object.entries(properties)) {
    const p = prop as any
    if (p.enum) {
      obj[key] = p.enum[0]
    } else if (p.type === 'string') {
      if (p.format === 'email') obj[key] = 'test@example.com'
      else if (p.format === 'uri' || p.format === 'url') obj[key] = 'https://example.com'
      else if (p.format === 'date') obj[key] = '2026-01-01'
      else if (p.format === 'date-time') obj[key] = '2026-01-01T00:00:00Z'
      else obj[key] = `test_${key}`
    } else if (p.type === 'integer' || p.type === 'number') {
      obj[key] = p.minimum ?? 1
    } else if (p.type === 'boolean') {
      obj[key] = true
    } else if (p.type === 'array') {
      obj[key] = []
    } else if (p.type === 'object') {
      obj[key] = {}
    } else {
      obj[key] = 'test'
    }
  }
  return JSON.stringify(obj, null, 2)
}

/**
 * 格式化响应体为可读字符串
 * JSON 字符串 → pretty print；对象 → JSON.stringify；null/undefined → "(空)"
 */
export function formatBody(data: any): string {
  if (data === null || data === undefined) return '(空)'
  if (typeof data === 'string') {
    try { return JSON.stringify(JSON.parse(data), null, 2) } catch { return data }
  }
  return JSON.stringify(data, null, 2)
}
