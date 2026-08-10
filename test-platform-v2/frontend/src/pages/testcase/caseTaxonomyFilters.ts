import type { TaxonomyModuleNode } from '@/api/testcase'

export interface CaseTaxonomySelection {
  surface: string
  domain: string
  modulePath: string
  nature: string
}
export interface ModuleFilterOption {
  value: string
  label: string
}

export function flattenTaxonomyModules(
  nodes: TaxonomyModuleNode[],
): ModuleFilterOption[] {
  return nodes.flatMap((node) => [
    { value: node.path, label: `${node.path} (${node.count})` },
    ...flattenTaxonomyModules(node.children),
  ])
}

export function buildCaseListParams(
  selection: CaseTaxonomySelection,
  base: Record<string, string | number>,
): Record<string, string | number> {
  return {
    ...base,
    ...(selection.surface ? { surface: selection.surface } : {}),
    ...(selection.domain ? { taxonomy_domain: selection.domain } : {}),
    ...(selection.modulePath ? { taxonomy_module: selection.modulePath } : {}),
    ...(selection.nature ? { positive_negative: selection.nature } : {}),
  }
}

export function countDirectCases(parentCount: number, childCounts: number[]): number {
  const childrenTotal = childCounts.reduce((total, count) => total + count, 0)
  // 后端异常（子级合计 > 父级）时按 0 处理，不显示负数。
  return Math.max(0, parentCount - childrenTotal)
}
