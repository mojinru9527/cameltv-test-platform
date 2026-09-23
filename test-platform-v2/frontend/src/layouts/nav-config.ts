import type { MenuItem } from '@/types'

/**
 * batch-259（B2-6 菜单收敛）导航模型 —— 角色友好「4 入口 + 专家区」。
 * 事实源：docs/platform-refactor/09-platform-landing-plan.md §2.1 +
 * 01(§3.1 测试工程师界面入口收敛) + 02(功能 ABCD 白名单)。
 *
 * 侧边栏顶层 = **4 个一级入口**（tester 默认可见）+ **1 个专家区**（二级 + 权限门禁）：
 *   ① 我的待办    menu:workbench
 *   ② 版本验收    版本任务 / 智能测试(方案) / 发布包 / 需求源
 *   ③ 结果与缺陷  缺陷管理 / 报告中心
 *   ④ 知识库      menu:knowledge
 *   专家区        资产（用例/接口/UI/数据/环境）、引擎与配置、个人、系统；
 *                 按 资产/引擎与配置/个人/系统 分桶，空桶与空容器都不渲染。
 *
 * 未命中任何分桶的 code（含未来新增菜单）一律落入「更多」桶（fail-safe，不污染一级入口）。
 * 一级入口数量由 `PRIMARY_ENTRY_LIMIT` 固化，并有测试断言守着，防止"用着用着又长回去"。
 */

/**
 * 一级入口数量上限（tester 默认可见）。改动此值必须同步更新 nav-config.test.ts 的断言。
 * 专家区不计入该额度：它是二级容器 + 权限门禁，不是第 5 个平级入口。
 */
export const PRIMARY_ENTRY_LIMIT = 4

/**
 * batch-272（选项 B：按角色瘦身）—— 非管理员在专家区里**保留**的高频项。
 *
 * 其余模块不再出现在侧栏，但**没有下架**：它们仍由 `/system/menus` 返回（后端按角色权限过滤），
 * 因此命令面板（⌘K / Ctrl+K）仍能搜到并直达——见 `CommandPalette` 的 `visibleMenuPaths` 与
 * `buildNavigation().searchOnly`。这样"侧栏短"与"页面可达"不再互相牺牲。
 *
 * 保留口径：日常工作台面（资产桶）= 用例服务 / 接口测试 / UI 自动化 / 测试数据集 / 目标环境。
 */
export const EXPERT_KEEP_CODES: readonly string[] = [
  'menu:testcase',
  'menu:apitest',
  'menu:uitest',
  'menu:dataset',
  'menu:environment',
]

export interface BuildNavigationOptions {
  /**
   * true = 按角色瘦身（非管理员）：专家区只渲染 `EXPERT_KEEP_CODES`，
   * 其余菜单进入 `searchOnly`（不渲染、但可搜）；false/缺省 = 现状（全部进分桶）。
   */
  slimExpert?: boolean
}

/**
 * 专家区折叠容器展开状态 localStorage key（"1"=展开，其余/缺省=收起）。
 * 键名沿用 batch-212 的历史值，避免用户已保存的展开状态在本次收敛后失效。
 */
export const EXPERT_AREA_STORAGE_KEY = 'sidebar:assets-more-open'

export type MainRowLinkDef = { kind: 'link'; code: string }
export type MainRowGroupDef = { kind: 'group'; label: string; codes: readonly string[] }
export type MainRowDef = MainRowLinkDef | MainRowGroupDef

/** 顶层 4 个一级入口蓝图（顺序即展示顺序）。 */
export const MAIN_ROW_DEFS: readonly MainRowDef[] = [
  { kind: 'link', code: 'menu:workbench' }, // ① 我的待办
  {
    kind: 'group',
    label: '版本验收', // ②
    codes: ['menu:versiontask', 'menu:missions', 'menu:versionmission', 'menu:requirement'],
  },
  { kind: 'group', label: '结果与缺陷', codes: ['menu:defect', 'menu:report'] }, // ③
  { kind: 'link', code: 'menu:knowledge' }, // ④ 知识库
]

export interface ExpertBucketDef {
  label: string
  codes: readonly string[]
}

/** 专家区分桶（顺序即展示顺序；fail-safe 未命中 code 落入「更多」）。 */
export const EXPERT_BUCKET_DEFS: readonly ExpertBucketDef[] = [
  {
    label: '资产',
    codes: [
      'menu:testcase',    // 用例服务：资产库保留（用户定稿）
      'menu:apitest',     // 接口测试：资产库 + 执行能力（保留）
      'menu:uitest',      // UI 自动化：资产库 + 执行能力（保留）
      'menu:dataset',     // 测试数据集：资产（向导自动带出）
      'menu:environment', // 目标环境：资产（向导自动带出）
    ],
  },
  {
    label: '引擎与配置',
    codes: [
      'menu:dsh_tasks',      // DSH 任务：执行引擎（02 §2 B）
      'menu:ai_config',      // AI 配置：专家/管理员
      'menu:lanhu_evidence', // 蓝湖证据包：专家/管理员
      'menu:runtime',        // Durable Runtime：引擎专家
      'menu:integration',    // 集成
      'menu:notify',         // 通知
    ],
  },
  { label: '个人', codes: ['menu:schedule', 'menu:myproject', 'menu:metrics', 'menu:onboarding'] },
  { label: '系统', codes: ['menu:system'] },
]

export type MainNavRow =
  | { kind: 'link'; item: MenuItem }
  | { kind: 'group'; label: string; items: MenuItem[] }

export interface ExpertSection {
  label: string
  items: MenuItem[]
}

export interface NavigationModel {
  /** 顶层一级入口（≤ PRIMARY_ENTRY_LIMIT；缺权限的行自动省略）。 */
  mainRows: MainNavRow[]
  /** 专家区分桶（仅非空）。 */
  expertSections: ExpertSection[]
  /**
   * 侧栏**不渲染**但仍在用户权限内的菜单（batch-272 瘦身后产生）。
   * 它们必须在命令面板里可搜——这是"瘦身不丢功能"的对账口径。
   */
  searchOnly: MenuItem[]
}

const bySort = (a: MenuItem, b: MenuItem) => a.sort - b.sort

/**
 * 按 code 从用户可见菜单（后端已按角色权限过滤）组装 5 行 + 分桶。
 * fail-safe：新菜单 code 不会污染顶层，一律落入「更多」桶。
 */
export function buildNavigation(
  menus: MenuItem[],
  options: BuildNavigationOptions = {},
): NavigationModel {
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
    if (items.length === 0) continue
    for (const item of items) seen.add(item.code)
    mainRows.push({ kind: 'group', label: def.label, items })
  }

  // 分桶
  const bucketItems = new Map<string, MenuItem[]>()
  const leftover: MenuItem[] = []
  for (const menu of menus) {
    if (seen.has(menu.code)) continue
    const bucket = EXPERT_BUCKET_DEFS.find((b) => b.codes.includes(menu.code))
    if (bucket) {
      const list = bucketItems.get(bucket.label) ?? []
      list.push(menu)
      bucketItems.set(bucket.label, list)
    } else {
      leftover.push(menu)
    }
  }

  const expertSections: ExpertSection[] = []
  for (const bucket of EXPERT_BUCKET_DEFS) {
    const list = (bucketItems.get(bucket.label) ?? []).sort(bySort)
    if (bucket.label === '更多') {
      // 未命中分桶的新 code 并入「更多」桶（fail-safe，保持展示顺序）
      list.push(...leftover.sort(bySort))
    }
    if (list.length > 0) expertSections.push({ label: bucket.label, items: list })
  }
  if (leftover.length > 0 && !expertSections.some((s) => s.label === '更多')) {
    expertSections.push({ label: '更多', items: leftover.sort(bySort) })
  }

  if (!options.slimExpert) {
    return { mainRows, expertSections, searchOnly: [] }
  }

  // ── 选项 B：按角色瘦身（batch-272）────────────────────────────────
  // 专家区只留 EXPERT_KEEP_CODES；其余（含 fail-safe 的「更多」）转 searchOnly：
  // 不渲染 ≠ 下架，命令面板仍可搜到（MainLayout 把 /system/menus 的完整路径集传给面板）。
  const keep = new Set(EXPERT_KEEP_CODES)
  const slimSections: ExpertSection[] = []
  const searchOnly: MenuItem[] = []
  for (const section of expertSections) {
    const kept: MenuItem[] = []
    for (const item of section.items) {
      if (keep.has(item.code)) kept.push(item)
      else searchOnly.push(item)
    }
    if (kept.length > 0) slimSections.push({ label: section.label, items: kept })
  }
  return { mainRows, expertSections: slimSections, searchOnly: searchOnly.sort(bySort) }
}

/** 路径是否命中分桶任一项（命中时「资产与更多」自动展开）。查询串不参与比较。 */
export function isPathInItems(pathname: string, items: MenuItem[]): boolean {
  return items.some((menu) => {
    const base = menu.path.split('?')[0]
    return base !== '' && (pathname === base || (base !== '/' && pathname.startsWith(base)))
  })
}

/** 读取专家区持久化展开状态（默认收起）。 */
export function readAssetsMoreOpen(storage: Pick<Storage, 'getItem'>): boolean {
  return storage.getItem(EXPERT_AREA_STORAGE_KEY) === '1'
}

/** 持久化专家区展开状态。 */
export function writeAssetsMoreOpen(storage: Pick<Storage, 'setItem'>, open: boolean): void {
  storage.setItem(EXPERT_AREA_STORAGE_KEY, open ? '1' : '0')
}
