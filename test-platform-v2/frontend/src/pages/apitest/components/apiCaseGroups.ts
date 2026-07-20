export interface ApiCaseGroup {
  key: string
  name: string        // Display name: "[GET] /api/user/list"
  method: string
  endpoint: string
  cases: any[]
}

/**
 * Group test cases by API endpoint.
 *
 * Priority:
 * 1. If cases share the same `api_spec_ref`, group them together (same source endpoint).
 * 2. Otherwise, group by `method:endpoint` combination.
 *
 * Example: Endpoint "POST /api/c" with 5 cases → one group with 5 sub-items.
 */
export function groupApiCases(cases: any[]): ApiCaseGroup[] {
  // First pass: build groups by api_spec_ref (preferred) or method:endpoint (fallback)
  const map = new Map<string, { method: string; endpoint: string; items: any[] }>()

  for (const c of cases) {
    const method = c.api_method || 'GET'
    const rawEndpoint = c.api_endpoint || '/'

    // Preferred key: api_spec_ref (stable reference to source endpoint)
    const specRef = c.api_spec_ref
    let key: string
    let canonicalEndpoint: string

    if (specRef && specRef !== '__ungrouped__') {
      key = specRef
      // Use the shortest endpoint in the group as the canonical display endpoint
      canonicalEndpoint = rawEndpoint
    } else {
      // Fallback: method + endpoint path (strip query string for grouping)
      const pathOnly = rawEndpoint.split('?')[0]
      key = `${method}:${pathOnly}`
      canonicalEndpoint = pathOnly
    }

    if (!map.has(key)) {
      map.set(key, { method, endpoint: canonicalEndpoint, items: [] })
    } else {
      // Update to the shorter/cleaner endpoint for display
      const existing = map.get(key)!
      if (canonicalEndpoint.length < existing.endpoint.length) {
        existing.endpoint = canonicalEndpoint
      }
      if (method !== 'GET' && existing.method === 'GET') {
        existing.method = method
      }
    }
    map.get(key)!.items.push(c)
  }

  return Array.from(map.entries()).map(([key, group]) => {
    const name = `[${group.method}] ${group.endpoint}`
    return { key, name, method: group.method, endpoint: group.endpoint, cases: group.items }
  })
}
