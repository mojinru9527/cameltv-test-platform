interface MindmapCase {
  domain?: string
  module?: string
  case_type?: string
  surface?: string
  priority?: string
  title?: string
  preconditions?: string
  expected_result?: string
}

interface ModuleBranch {
  name: string
  children: Map<string, ModuleBranch>
  cases: MindmapCase[]
}

export const SURFACE_ORDER = ['用户端', '运营后台', '接口测试', '其他'] as const

export type CaseSurface = typeof SURFACE_ORDER[number]

export function caseSurfaceOf(testCase: Pick<MindmapCase, 'surface'>): CaseSurface {
  if (SURFACE_ORDER.includes(testCase.surface as CaseSurface)) {
    return testCase.surface as CaseSurface
  }
  return '其他'
}

export function availableCaseSurfaces(cases: readonly Pick<MindmapCase, 'surface'>[]): CaseSurface[] {
  const present = new Set(cases.map(caseSurfaceOf))
  return SURFACE_ORDER.filter((surface) => present.has(surface))
}

export function splitModulePath(module = ''): string[] {
  return module.split(/[/\\>＞]+/).map((segment) => segment.trim()).filter(Boolean).length
    ? module.split(/[/\\>＞]+/).map((segment) => segment.trim()).filter(Boolean)
    : ['未分类']
}

export function buildCaseMindmapMarkdown(cases: MindmapCase[]): string {
  if (!cases.length) return '# 测试用例\n\n暂无用例数据'

  const surfaces = new Map<CaseSurface, Map<string, Map<string, ModuleBranch>>>()
  for (const testCase of cases) {
    const surface = caseSurfaceOf(testCase)
    const domain = testCase.domain?.trim() || '未分类'
    const domains = surfaces.get(surface) || new Map()
    surfaces.set(surface, domains)
    const modules = domains.get(domain) || new Map()
    domains.set(domain, modules)

    let branch = modules
    let leaf: ModuleBranch | undefined
    for (const segment of splitModulePath(testCase.module)) {
      const node = branch.get(segment) || { name: segment, children: new Map(), cases: [] }
      branch.set(segment, node)
      leaf = node
      branch = node.children
    }
    leaf?.cases.push(testCase)
  }

  const lines = ['# 测试用例', '']
  const renderBranch = (branch: ModuleBranch, depth: number) => {
    const headingDepth = Math.min(depth, 6)
    lines.push(`${'#'.repeat(headingDepth)} ${branch.name}`)
    for (const testCase of branch.cases) {
      const label = `[${testCase.priority || 'P2'}] ${testCase.title || '未命名用例'}`
      if (headingDepth < 6) lines.push(`${'#'.repeat(headingDepth + 1)} ${label}`)
      else lines.push(`- ${label}`)
      if (testCase.preconditions) lines.push(`  - 前置: ${testCase.preconditions}`)
      if (testCase.expected_result) lines.push(`  - 预期: ${testCase.expected_result}`)
    }
    for (const child of [...branch.children.values()].sort((a, b) => a.name.localeCompare(b.name))) {
      renderBranch(child, depth + 1)
    }
  }

  for (const surface of SURFACE_ORDER) {
    const domains = surfaces.get(surface)
    if (!domains) continue
    lines.push(`## ${surface}`)
    for (const [domain, modules] of [...domains.entries()].sort(([a], [b]) => a.localeCompare(b))) {
      lines.push(`### ${domain}`)
      for (const module of [...modules.values()].sort((a, b) => a.name.localeCompare(b.name))) {
        renderBranch(module, 4)
      }
    }
  }
  return lines.join('\n')
}
