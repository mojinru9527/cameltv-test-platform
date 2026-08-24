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
 * 根据 OpenAPI schema 属性生成示例值（A组：优先契约真实值 example → default → enum[0]，
 * 缺失时再按类型兜底；不再默认产出占位假数据）。
 */
export function sampleValueForProp(prop: Record<string, any>, key?: string): any {
  const p = (prop || {}) as Record<string, any>
  if ('example' in p && p.example !== undefined && p.example !== null) return p.example
  if ('default' in p && p.default !== undefined && p.default !== null) return p.default
  if (Array.isArray(p.enum) && p.enum.length > 0) return p.enum[0]
  if (p.type === 'string') {
    if (p.format === 'email') return 'test@example.com'
    if (p.format === 'uri' || p.format === 'url') return 'https://example.com'
    if (p.format === 'date') return '2026-01-01'
    if (p.format === 'date-time') return '2026-01-01T00:00:00Z'
    return `test_${key || 'value'}`
  }
  if (p.type === 'integer' || p.type === 'number') return p.minimum ?? 1
  if (p.type === 'boolean') return true
  if (p.type === 'array') return []
  if (p.type === 'object') return {}
  return 'test'
}

/**
 * 根据 OpenAPI schema properties 生成示例请求体 JSON 字符串
 * 用于 pre-fill endpoint 的 Body 编辑区
 */
export function buildSampleBody(properties: Record<string, any>): string {
  const obj: Record<string, any> = {}
  for (const [key, prop] of Object.entries(properties || {})) {
    obj[key] = sampleValueForProp(prop as any, key)
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
