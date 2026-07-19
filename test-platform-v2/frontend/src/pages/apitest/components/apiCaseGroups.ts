export interface ApiCaseGroup {
  key: string
  name: string        // Display name extracted from the first case's title or api_spec_ref
  api_spec_ref: string
  cases: any[]
}

export function groupApiCases(cases: any[]): ApiCaseGroup[] {
  const map = new Map<string, any[]>()

  for (const c of cases) {
    const ref = c.api_spec_ref || '__ungrouped__'
    if (!map.has(ref)) map.set(ref, [])
    map.get(ref)!.push(c)
  }

  return Array.from(map.entries()).map(([ref, items]) => {
    // Extract display name from first case title
    // Title format: "【正向】接口名 - 正常请求" → extract "接口名"
    const firstTitle = items[0]?.title || ''
    const nameMatch = firstTitle.match(/】(.+?)(?:\s-|$)/)
    const name = nameMatch ? nameMatch[1] : (ref === '__ungrouped__' ? '未分组' : ref)

    return { key: ref, name, api_spec_ref: ref, cases: items }
  })
}
