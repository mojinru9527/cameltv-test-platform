export interface ApiCaseGroup {
  key: string
  name: string        // Display name extracted from the first case's title or api_spec_ref
  method: string      // HTTP method of the group
  endpoint: string    // Clean endpoint path (no query string)
  api_spec_ref: string
  cases: any[]
}

export function groupApiCases(cases: any[]): ApiCaseGroup[] {
  const map = new Map<string, { method: string; endpoint: string; items: any[] }>()

  for (const c of cases) {
    const specRef = c.api_spec_ref
    let key: string
    let method: string
    let endpoint: string

    if (specRef && specRef !== '__ungrouped__') {
      key = specRef
      method = c.api_method || 'GET'
      endpoint = (c.api_endpoint || '/').split('?')[0]
    } else {
      method = c.api_method || 'GET'
      const pathOnly = (c.api_endpoint || '/').split('?')[0]
      key = `${method}:${pathOnly}`
      endpoint = pathOnly
    }

    if (!map.has(key)) {
      map.set(key, { method, endpoint, items: [] })
    }
    map.get(key)!.items.push(c)
  }

  return Array.from(map.entries()).map(([key, { method, endpoint, items }]) => {
    // Extract display name from first case title
    // Title format: "【正向】接口名 - 正常请求" → extract "接口名"
    const firstTitle = items[0]?.title || ''
    const nameMatch = firstTitle.match(/】(.+?)(?:\s-|$)/)
    const name = nameMatch ? nameMatch[1] : (key === '__ungrouped__' ? '未分组' : key)

    return { key, name, method, endpoint, api_spec_ref: key, cases: items }
  })
}
