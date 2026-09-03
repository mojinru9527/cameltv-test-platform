import type { MenuItem } from '@/types'

/**
 * batch-212（B2 入口收敛）导航模型 —— 角色友好「5 入口 + 资产与更多分桶」。
 * 事实源：docs/platform-refactor/01(§3.1 测试工程师界面 ≤5 一级入口) +
 * 02(功能 ABCD 白名单) + docs/superpowers/plans/2026-09-02-platform-refactor-rollout.md(B2)。
 *
 * 侧边栏顶层固定 5 行（菜单数据仍由后端按角色权限过滤，前端只负责「按 code 组装展示」）：
 *   1 工作台      menu:workbench
 *   2 版本验收    版本验收任务 menu:versiontask + 智能测试任务 menu:missions + 版本发布包 menu:versionmission
 *   3 结果与缺陷  报告中心 menu:report + 缺陷管理 menu:defect
 *   4 知识中心    menu:knowledge
 *   5 资产与更多  其余全部模块，按 资产/更多/专家/系统 分桶（空桶/空容器不渲染）
 * 未命中任何分桶的 code（含未来新增菜单）一律落入「更多」桶（fail-safe）。
 */

/** 「资产与更多」折叠容器展开状态 localStorage key（"1"=展开，其余/缺省=收起）。 */
export const ASSETS_MORE_STORAGE_KEY = 'sidebar:assets-more-open'

export type MainRowLinkDef = { kind: 'link'; code: string }
export type MainRowGroupDef = { kind: 'group'; label: string; codes: readonly string[] }
export type MainRowDef = MainRowLinkDef | MainRowGroupDef

/** 顶层 5 行蓝图（顺序即展示顺序）。 */
export const MAIN_ROW_DEFS: readonly MainRowDef[] = [
  { kind: 'link', code: 'menu:workbench' },
  { kind: 'group', label: '版本验收', codes: ['menu:versiontask', 'menu:missions', 'menu:versionmission'] },
  { kind: 'group', label: '结果与缺陷', codes: ['menu:report', 'menu:defect'] },
  { kind: 'link', code: 'menu:knowledge' },
]

export interface AssetBucketDef {
  label: string
  codes: readonly string[]
}

/** 资产与更多 分桶（顺序即展示顺序；fail-safe 未命中 code 落入「更多」）。 */
export const ASSET_BUCKET_DEFS: readonly AssetBucketDef[] = [
  {
    label: '资产',
    codes: [
      'menu:requirement', // 需求文档：需求源资产（02 §2 A）
      'menu:testcase',    // 用例服务：资产库保留（用户定稿）
      'menu:apitest',     // 接口测试：资产库 + 执行能力（保留）
      'menu:uitest',      // UI 自动化：资产库 + 执行能力（保留）
      'menu:dataset',     // 测试数据集：资产（向导自动带出）
      'menu:environment', // 目标环境：资产（向导自动带出）
    ],
  },
  { label: '更多', codes: ['menu:schedule', 'menu:myproject', 'menu:metrics', 'menu:onboarding'] },
  {
    label: '专家',
    codes: [
      'menu:dsh_tasks',      // DSH 任务：执行引擎（02 §2 B）
      'menu:ai_config',      // AI 配置：专家/管理员
      'menu:lanhu_evidence', // 蓝湖证据包：专家/管理员
      'menu:runtime',        // Durable Runtime：引擎专家
    ],
  },
  { label: '系统', codes: ['menu:system', 'menu:integration', 'menu:notify'] },
]

export type MainNavRow =
  | { kind: 'link'; item: MenuItem }
  | { kind: 'group'; label: string; items: MenuItem[] }

export interface AssetSection {
  label: string
  items: MenuItem[]
}

export interface NavigationModel {
  /** 顶层 5 行（缺权限的行自动省略）。 */
  mainRows: MainNavRow[]
  /** 资产与更多 分桶（仅非空）。 */
  assetSections: AssetSection[]
}

const bySort = (a: MenuItem, b: MenuItem) => a.sort - b.sort

/**
 * 按 code 从用户可见菜单（后端已按角色权限过滤）组装 5 行 + 分桶。
 * fail-safe：新菜单 code 不会污染顶层，一律落入「更多」桶。
 */
export function buildNavigation(menus: MenuItem[]): NavigationModel {
  const byCode = new Map<string, MenuItem>()
  for (const menu of menus) {
    if (menu.code && !byCode.has(menu.code)) byCode.set(menu.code, menu)
  }

  const mainRows: MainNavRow[] = []
  const seen = new Set<string>()

  for (const def of MAIN_ROW_DEFS) {
    if (def.kind === 'link') {
      const item = byCode.get(def.code)
      if (!item) continue
      mainRows.push({ kind: 'link', item })
      seen.add(def.code)
      continue
    }
    const items = def.codes
      .map((code) => byCode.get(code))
      .filter((item): item is MenuItem => Boolean(item))
      .sort(bySort)
    if (items.length === 0) continue
    for (const item of items) seen.add(item.code)
    mainRows.push({ kind: 'group', label: def.label, items })
  }

  // 分桶
  const bucketItems = new Map<string, MenuItem[]>()
  const leftover: MenuItem[] = []
  for (const menu of menus) {
    if (seen.has(menu.code)) continue
    const bucket = ASSET_BUCKET_DEFS.find((b) => b.codes.includes(menu.code))
    if (bucket) {
      const list = bucketItems.get(bucket.label) ?? []
      list.push(menu)
      bucketItems.set(bucket.label, list)
    } else {
      leftover.push(menu)
    }
  }

  const assetSections: AssetSection[] = []
  for (const bucket of ASSET_BUCKET_DEFS) {
    const list = (bucketItems.get(bucket.label) ?? []).sort(bySort)
    if (bucket.label === '更多') {
      // 未命中分桶的新 code 并入「更多」桶（fail-safe，保持展示顺序）
      list.push(...leftover.sort(bySort))
    }
    if (list.length > 0) assetSections.push({ label: bucket.label, items: list })
  }
  if (leftover.length > 0 && !assetSections.some((s) => s.label === '更多')) {
    assetSections.push({ label: '更多', items: leftover.sort(bySort) })
  }

  return { mainRows, assetSections }
}

/** 路径是否命中分桶任一项（命中时「资产与更多」自动展开）。查询串不参与比较。 */
export function isPathInItems(pathname: string, items: MenuItem[]): boolean {
  return items.some((menu) => {
    const base = menu.path.split('?')[0]
    return base !== '' && (pathname === base || (base !== '/' && pathname.startsWith(base)))
  })
}

/** 读取「资产与更多」持久化展开状态（默认收起）。 */
export function readAssetsMoreOpen(storage: Pick<Storage, 'getItem'>): boolean {
  return storage.getItem(ASSETS_MORE_STORAGE_KEY) === '1'
}

/** 持久化「资产与更多」展开状态。 */
export function writeAssetsMoreOpen(storage: Pick<Storage, 'setItem'>, open: boolean): void {
  storage.setItem(ASSETS_MORE_STORAGE_KEY, open ? '1' : '0')
}