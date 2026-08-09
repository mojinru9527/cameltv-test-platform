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
  return scopes.length > 0 ? scopes.join('、') : '无作用域'
}
