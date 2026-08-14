/**
 * 域命名体系收敛（Batch 182 / FIX-173-P3-04）
 *
 * 背景：用例「所属域」与追溯「按域覆盖」长期混排五种命名范式：
 *   `用户端/xxx`、`运营后台/xxx`、`接口测试/xxx`、`体育-运营后台-功能` 式连字符、
 *   以及裸域（UGC、广告…）。batch-178 已为域下拉做分组+搜索，但组名/口径与
 *   case_surface 分类不一致。
 *
 * 本模块统一展示口径（与后端回填脚本 scripts/backfill-domain-naming-b182.py 同规则）：
 *   - `用户端/`、`运营后台/`、`接口测试/` 直接取前缀（含平台名本身的裸值，如 `接口测试`）；
 *   - 连字符平台前缀（`运营后台-xxx`）与 `体育-运营后台-*` 归「运营后台」组（仅展示归组，不改库）；
 *   - 裸域（UGC、广告等）归「用户端」组，标签保留原名并补前缀，如 `用户端/广告`；
 *   - 无法归类的（空值/空白）归「其他」，展示为「未分类」。
 */
export type DomainGroup = '用户端' | '运营后台' | '接口测试' | '其他'

/** 分组展示顺序：用户端 / 运营后台 / 接口测试 / 其他。 */
export const DOMAIN_GROUP_ORDER: readonly DomainGroup[] = ['用户端', '运营后台', '接口测试', '其他']

export interface DomainGrouping {
  group: DomainGroup
  /** 展示标签：裸域已补前缀（如 `用户端/广告`），其余保留原名。 */
  label: string
}

const PLATFORM_GROUPS: ReadonlyArray<{ group: DomainGroup; prefix: string }> = [
  { group: '用户端', prefix: '用户端' },
  { group: '运营后台', prefix: '运营后台' },
  { group: '接口测试', prefix: '接口测试' },
]

/**
 * 按 batch-182 规范把原始 domain 值归组并生成展示标签。
 * 空值/空白归「其他」并展示为「未分类」。
 */
export function groupDomainLabel(domain: string | null | undefined): DomainGrouping {
  const d = (domain ?? '').trim()
  if (!d) return { group: '其他', label: '未分类' }
  for (const { group, prefix } of PLATFORM_GROUPS) {
    // 平台名本身（`接口测试`）或平台前缀 + 分隔符（`用户端/首页`、`运营后台-热门比赛配置`）
    if (d === prefix || d.startsWith(`${prefix}/`) || d.startsWith(`${prefix}-`)) {
      return { group, label: d }
    }
  }
  if (d.startsWith('体育-运营后台')) {
    return { group: '运营后台', label: d }
  }
  // 裸域 → 用户端组，标签补前缀（与回填脚本归一映射一致）
  return { group: '用户端', label: `用户端/${d}` }
}

/**
 * 按 DOMAIN_GROUP_ORDER 把条目聚合为分组列表（组内保持传入顺序）。
 * 供域下拉分组与 trace 按域覆盖轴复用同一口径。
 */
export function groupDomains<T>(
  items: readonly T[],
  getDomain: (item: T) => string,
): Array<[DomainGroup, T[]]> {
  const map = new Map<DomainGroup, T[]>()
  for (const item of items) {
    const { group } = groupDomainLabel(getDomain(item))
    const bucket = map.get(group)
    if (bucket) bucket.push(item)
    else map.set(group, [item])
  }
  return DOMAIN_GROUP_ORDER
    .filter((group) => map.has(group))
    .map((group) => [group, map.get(group)!])
}

/** 组排序比较器：按 DOMAIN_GROUP_ORDER 排序（未知名次兜底排最后）。 */
export function compareDomainGroups(a: DomainGroup, b: DomainGroup): number {
  const ia = DOMAIN_GROUP_ORDER.indexOf(a)
  const ib = DOMAIN_GROUP_ORDER.indexOf(b)
  return (ia === -1 ? DOMAIN_GROUP_ORDER.length : ia) - (ib === -1 ? DOMAIN_GROUP_ORDER.length : ib)
}
