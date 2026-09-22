import { describe, expect, it } from 'vitest'

import type { MenuItem } from '@/types'
import {
  EXPERT_KEEP_CODES,
  EXPERT_AREA_STORAGE_KEY,
  PRIMARY_ENTRY_LIMIT,
  buildNavigation,
  isPathInItems,
  readAssetsMoreOpen,
  writeAssetsMoreOpen,
  type NavigationModel,
} from './nav-config'

function menu(code: string, path: string, sort: number): MenuItem {
  return { code, name: code, path, icon: '', sort }
}

// tester 可见菜单（batch-259：menu:testplan 已删除；notify/integration 软下线默认不可见）
const TESTER_MENUS: MenuItem[] = [
  menu('menu:workbench', '/workbench', 1),
  menu('menu:requirement', '/requirement', 3),
  menu('menu:versionmission', '/release-bundles', 4),
  menu('menu:knowledge', '/knowledge', 5),
  menu('menu:testcase', '/testcase', 7),
  menu('menu:apitest', '/apitest', 9),
  menu('menu:uitest', '/uitest', 10),
  menu('menu:schedule', '/schedule', 12),
  menu('menu:report', '/report', 13),
  menu('menu:myproject', '/my-projects', 15),
  menu('menu:defect', '/defect', 16),
  menu('menu:dataset', '/dataset', 17),
  menu('menu:environment', '/environment', 20),
  menu('menu:dsh_tasks', '/dsh-tasks', 22),
  menu('menu:ai_config', '/ai-config', 23),
  menu('menu:lanhu_evidence', '/lanhu-evidence', 23),
  menu('menu:missions', '/missions', 24),
  menu('menu:runtime', '/admin/workers', 25),
]

function flattenMain(model: NavigationModel): string[] {
  return model.mainRows.flatMap((row) =>
    row.kind === 'link' ? [row.item.code] : [row.label, ...row.items.map((i) => i.code)],
  )
}

describe('batch-259 buildNavigation（4 入口 + 专家区）', () => {
  it('tester 可见菜单 → 一级入口恰好 4 个（B2-6 的 DoD：≤4 + 专家区）', () => {
    const model = buildNavigation(TESTER_MENUS)
    expect(flattenMain(model)).toEqual([
      'menu:workbench', // 1 工作台
      '版本验收', 'menu:missions', 'menu:versionmission', 'menu:requirement',
      '结果与缺陷', 'menu:defect', 'menu:report',
      'menu:knowledge', // 4
    ])
    expect(model.mainRows).toHaveLength(PRIMARY_ENTRY_LIMIT)
    expect(model.mainRows.length).toBeLessThanOrEqual(4)
    // 第 5 个控件是专家区容器，不算一级入口
    expect(model.expertSections.length).toBeGreaterThan(0)
  })

  it('任何角色/菜单集合下，一级入口都不超过 4（防止回涨）', () => {
    const adminMenus = [
      ...TESTER_MENUS,
      menu('menu:system', '/system', 14),
      menu('menu:notify', '/notify', 19),
      menu('menu:integration', '/integration', 18),
      menu('menu:versiontask', '/version-tasks', 30),
    ]
    for (const menus of [TESTER_MENUS, adminMenus, [], [menu('menu:workbench', '/workbench', 1)]]) {
      expect(buildNavigation(menus).mainRows.length).toBeLessThanOrEqual(PRIMARY_ENTRY_LIMIT)
    }
  })

  it('专家区分桶：资产含用例/接口/UI/数据集/环境；引擎与配置含 DSH/AI/蓝湖/Runtime/集成/通知；个人含定时/我的项目；tester 无系统桶', () => {
    const model = buildNavigation(TESTER_MENUS)
    const labels = model.expertSections.map((s) => s.label)
    expect(labels).toEqual(['资产', '引擎与配置', '个人'])
    const byLabel = Object.fromEntries(model.expertSections.map((s) => [s.label, s.items.map((i) => i.code)]))
    expect(byLabel['资产']).toEqual([
      'menu:testcase', 'menu:apitest', 'menu:uitest', 'menu:dataset', 'menu:environment',
    ])
    expect(byLabel['引擎与配置']).toEqual([
      'menu:dsh_tasks', 'menu:ai_config', 'menu:lanhu_evidence', 'menu:runtime',
    ])
    expect(byLabel['个人']).toEqual(['menu:schedule', 'menu:myproject'])
  })

  it('用例/接口/UI 保留为资产（不删除、不在顶层平铺）', () => {
    const model = buildNavigation(TESTER_MENUS)
    const assetCodes = model.expertSections.flatMap((s) => s.items.map((i) => i.code))
    for (const code of ['menu:testcase', 'menu:apitest', 'menu:uitest']) {
      expect(assetCodes).toContain(code)
      expect(model.mainRows.some((r) => r.kind === 'link' && r.item.code === code)).toBe(false)
    }
  })

  it('admin（含系统菜单）→ 出现系统分桶', () => {
    const adminMenus = [...TESTER_MENUS, menu('menu:system', '/system', 14), menu('menu:notify', '/notify', 19), menu('menu:integration', '/integration', 18)]
    const model = buildNavigation(adminMenus)
    expect(model.expertSections.map((s) => s.label)).toEqual(['资产', '引擎与配置', '个人', '系统'])
    const system = model.expertSections.find((s) => s.label === '系统')!
    expect(system.items.map((i) => i.code)).toEqual(['menu:system'])
  })

  it('只读角色只显示有权限的报告，不补出任务入口', () => {
    const viewerMenus: MenuItem[] = [
      menu('menu:workbench', '/workbench', 1),
      menu('menu:requirement', '/requirement', 3),
      menu('menu:knowledge', '/knowledge', 5),
      menu('menu:report', '/report', 13),
      menu('menu:myproject', '/my-projects', 15),
      menu('menu:defect', '/defect', 16),
      menu('menu:dataset', '/dataset', 17),
    ]
    const model = buildNavigation(viewerMenus)
    expect(flattenMain(model)).toEqual([
      'menu:workbench',
      '版本验收', 'menu:requirement',
      '结果与缺陷', 'menu:defect', 'menu:report',
      'menu:knowledge',
    ])
  })

  it('fail-safe：未命中任何分桶的新 code 落入「更多」桶，不污染顶层', () => {
    const model = buildNavigation([...TESTER_MENUS, menu('menu:future_feature', '/future', 99)])
    expect(model.mainRows.length).toBe(PRIMARY_ENTRY_LIMIT)
    const more = model.expertSections.find((s) => s.label === '更多')!
    expect(more.items.map((i) => i.code)).toContain('menu:future_feature')
  })

  it('空输入安全', () => {
    const model = buildNavigation([])
    expect(model.mainRows).toEqual([])
    expect(model.expertSections).toEqual([])
  })

  it('每个可见菜单恰好出现一次，保留历史 URL 和菜单权限（隐藏≠删除）', () => {
    const menus = [...TESTER_MENUS, menu('menu:versiontask', '/version-tasks', 30)]
    const model = buildNavigation(menus)
    const group = model.mainRows.find((row) => row.kind === 'group' && row.label === '版本验收')
    expect(group?.kind).toBe('group')
    if (group?.kind !== 'group') throw new Error('Missing task/report navigation')
    expect(group.items.map((item) => item.path)).toEqual([
      '/version-tasks', '/missions', '/release-bundles', '/requirement',
    ])
    const displayed = [
      ...model.mainRows.flatMap((row) => row.kind === 'link' ? [row.item] : row.items),
      ...model.expertSections.flatMap((section) => section.items),
    ]
    expect(displayed).toHaveLength(menus.length)
    expect(new Set(displayed.map((item) => item.code)).size).toBe(menus.length)
    for (const item of displayed) expect(menus).toContain(item)
  })
})

describe('batch-212 isPathInItems（容器自动展开判定）', () => {
  const model = buildNavigation(TESTER_MENUS)
  const all = model.expertSections.flatMap((s) => s.items)

  it('命中资产路径（含子路径）', () => {
    expect(isPathInItems('/testcase', all)).toBe(true)
    expect(isPathInItems('/testcase/123', all)).toBe(true)
  })

  it('顶层行路径不命中容器项', () => {
    expect(isPathInItems('/workbench', all)).toBe(false)
    expect(isPathInItems('/knowledge', all)).toBe(false)
  })

  it('查询串不参与比较', () => {
    expect(isPathInItems('/knowledge', [menu('menu:x', '/knowledge?tab=graph', 0)])).toBe(true)
  })
})

describe('batch-212 「资产与更多」展开状态持久化', () => {
  it('默认收起（key 不存在 / 非 "1" 均为收起）', () => {
    const store = new Map<string, string>()
    const storage = { getItem: (k: string) => store.get(k) ?? null }
    expect(readAssetsMoreOpen(storage)).toBe(false)
    store.set(EXPERT_AREA_STORAGE_KEY, 'yes')
    expect(readAssetsMoreOpen(storage)).toBe(false)
  })

  it('写入后可读回；"1" 视为展开', () => {
    const store = new Map<string, string>()
    const storage = {
      getItem: (k: string) => store.get(k) ?? null,
      setItem: (k: string, v: string) => void store.set(k, v),
    }
    writeAssetsMoreOpen(storage, true)
    expect(store.get(EXPERT_AREA_STORAGE_KEY)).toBe('1')
    expect(readAssetsMoreOpen(storage)).toBe(true)
    writeAssetsMoreOpen(storage, false)
    expect(store.get(EXPERT_AREA_STORAGE_KEY)).toBe('0')
    expect(readAssetsMoreOpen(storage)).toBe(false)
  })
})

describe('batch-272 选项 B：按角色瘦身 + 搜索直达', () => {
  const sidebarCodes = (model: NavigationModel): string[] => [
    ...model.mainRows.flatMap((row) => (row.kind === 'link' ? [row.item.code] : row.items.map((i) => i.code))),
    ...model.expertSections.flatMap((section) => section.items.map((i) => i.code)),
  ]

  it('非管理员：专家区只留 EXPERT_KEEP_CODES，其余进入 searchOnly', () => {
    const menus = [...TESTER_MENUS, menu('menu:system', '/system', 40)]
    const model = buildNavigation(menus, { slimExpert: true })

    const kept = model.expertSections.flatMap((s) => s.items.map((i) => i.code))
    expect(kept.length).toBeGreaterThan(0)
    expect(kept.every((code) => EXPERT_KEEP_CODES.includes(code))).toBe(true)
    expect(kept).toEqual(['menu:testcase', 'menu:apitest', 'menu:uitest', 'menu:dataset', 'menu:environment'])

    const searchOnly = model.searchOnly.map((i) => i.code)
    expect(searchOnly).toContain('menu:dsh_tasks')
    expect(searchOnly).toContain('menu:ai_config')
    expect(searchOnly).toContain('menu:system')
    expect(searchOnly).not.toContain('menu:testcase')

    // 对账：侧栏 + 搜索直达 = 全部菜单，且每个 code 恰好一次（瘦身 ≠ 下架）
    const all = [...sidebarCodes(model), ...searchOnly]
    expect(all).toHaveLength(menus.length)
    expect(new Set(all).size).toBe(menus.length)
  })

  it('管理员：保持分桶全景，searchOnly 为空', () => {
    const model = buildNavigation(TESTER_MENUS)
    expect(model.searchOnly).toEqual([])
    expect(model.expertSections.map((s) => s.label)).toEqual(['资产', '引擎与配置', '个人'])
  })

  it('fail-safe：瘦身模式下未知新 code 不渲染但可搜', () => {
    const menus = [...TESTER_MENUS, menu('menu:future_feature', '/future', 99)]
    const model = buildNavigation(menus, { slimExpert: true })
    expect(sidebarCodes(model)).not.toContain('menu:future_feature')
    expect(model.searchOnly.map((i) => i.code)).toContain('menu:future_feature')
  })

  it('瘦身不改变一级入口数量（仍 ≤4）', () => {
    const model = buildNavigation(TESTER_MENUS, { slimExpert: true })
    expect(model.mainRows).toHaveLength(PRIMARY_ENTRY_LIMIT)
  })
})
