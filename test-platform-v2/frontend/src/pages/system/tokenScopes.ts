const SCOPE_LABELS: Record<string, string> = {
  trigger: '触发测试计划',
  api: '开放 API',
  read: '读取',
  write: '写入',
  'workers:register': 'Worker 注册',
}

export function formatTokenScopes(value: string[] | string): string {
  let scopes: string[] = []
  if (Array.isArray(value)) {
    scopes = value
  } else if (value) {
    try {
      const parsed = JSON.parse(value)
      if (Array.isArray(parsed)) scopes = parsed.map(String)
    } catch {
      scopes = value
        .replace(/^\[|\]$/g, '')
        .split(',')
        .map((item) => item.trim().replace(/^['"]|['"]$/g, ''))
        .filter(Boolean)
    }
  }
  return scopes.length > 0
    ? scopes.map((scope) => SCOPE_LABELS[scope] ?? scope).join('、')
    : '无作用域'
}
