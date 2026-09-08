import { describe, expect, it } from 'vitest'

import type { MenuItem } from '@/types'
import {
  ASSETS_MORE_STORAGE_KEY,
  buildNavigation,
  isPathInItems,
  readAssetsMoreOpen,
  writeAssetsMoreOpen,
  type NavigationModel,
} from './nav-config'

function menu(code: string, path: string, sort: number): MenuItem {
  return { code, name: code, path, icon: '', sort }
}

// tester 可见菜单（batch-212 后：menu:testplan 已删除；notify/integration 软下线默认不可见）
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

describe('batch-212 buildNavigation（5 入口 + 资产与更多分桶）', () => {
  it('tester 可见菜单 → 顶层恰好 5 个一级入口（4 主行 + 资产与更多容器）', () => {
    const model = buildNavigation(TESTER_MENUS)
    expect(flattenMain(model)).toEqual([
      'menu:workbench', // 1 工作台
      '任务与报告', 'menu:missions', 'menu:report', 'menu:versionmission',
      'menu:defect', // 3
      'menu:knowledge', // 4
    ])
    expect(model.assetSections.length).toBeGreaterThan(0)
    const totalEntries = model.mainRows.length + 1 // + 资产与更多容器
    expect(totalEntries).toBe(5)
  })

  it('分桶：资产含用例/接口/UI/数据集/环境/需求；更多含定时/我的项目；专家含 DSH/AI配置/蓝湖/Runtime；tester 无系统桶', () => {
    const model = buildNavigation(TESTER_MENUS)
    const labels = model.assetSections.map((s) => s.label)
    expect(labels).toEqual(['资产', '更多', '专家'])
    const byLabel = Object.fromEntries(model.assetSections.map((s) => [s.label, s.items.map((i) => i.code)]))
    expect(byLabel['资产']).toEqual([
      'menu:requirement', 'menu:testcase', 'menu:apitest', 'menu:uitest', 'menu:dataset', 'menu:environment',
    ])
    expect(byLabel['更多']).toEqual(['menu:schedule', 'menu:myproject'])
    expect(byLabel['专家']).toEqual(['menu:dsh_tasks', 'menu:ai_config', 'menu:lanhu_evidence', 'menu:runtime'])
  })

  it('用例/接口/UI 保留为资产（不删除、不在顶层平铺）', () => {
    const model = buildNavigation(TESTER_MENUS)
    const assetCodes = model.assetSections.flatMap((s) => s.items.map((i) => i.code))
    for (const code of ['menu:testcase', 'menu:apitest', 'menu:uitest']) {
      expect(assetCodes).toContain(code)
      expect(model.mainRows.some((r) => r.kind === 'link' && r.item.code === code)).toBe(false)
    }
  })

  it('admin（含系统菜单）→ 出现系统分桶', () => {
    const adminMenus = [...TESTER_MENUS, menu('menu:system', '/system', 14), menu('menu:notify', '/notify', 19), menu('menu:integration', '/integration', 18)]
    const model = buildNavigation(adminMenus)
    expect(model.assetSections.map((s) => s.label)).toEqual(['资产', '更多', '专家', '系统'])
    const system = model.assetSections.find((s) => s.label === '系统')!
    expect(system.items.map((i) => i.code)).toEqual(['menu:system', 'menu:integration', 'menu:notify'])
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
      '任务与报告', 'menu:report', 'menu:defect',
      'menu:knowledge',
    ])
  })

  it('fail-safe：未命中任何分桶的新 code 落入「更多」桶，不污染顶层', () => {
    const model = buildNavigation([...TESTER_MENUS, menu('menu:future_feature', '/future', 99)])
    expect(model.mainRows.length).toBe(4)
    const more = model.assetSections.find((s) => s.label === '更多')!
    expect(more.items.map((i) => i.code)).toContain('menu:future_feature')
  })

  it('空输入安全', () => {
    const model = buildNavigation([])
    expect(model.mainRows).toEqual([])
    expect(model.assetSections).toEqual([])
  })

  it('任务和报告只出现一次，保留历史 URL 和菜单权限', () => {
    const menus = [...TESTER_MENUS, menu('menu:versiontask', '/version-tasks', 30)]
    const model = buildNavigation(menus)
    const group = model.mainRows.find((row) => row.kind === 'group' && row.label === '任务与报告')
    expect(group?.kind).toBe('group')
    if (group?.kind !== 'group') throw new Error('Missing task/report navigation')
    expect(group.items.map((item) => item.path)).toEqual(['/version-tasks', '/missions', '/report', '/release-bundles'])
    const displayed = [
      ...model.mainRows.flatMap((row) => row.kind === 'link' ? [row.item] : row.items),
      ...model.assetSections.flatMap((section) => section.items),
    ]
    expect(displayed).toHaveLength(menus.length)
    expect(new Set(displayed.map((item) => item.code)).size).toBe(menus.length)
    for (const item of displayed) expect(menus).toContain(item)
  })
})

describe('batch-212 isPathInItems（容器自动展开判定）', () => {
  const model = buildNavigation(TESTER_MENUS)
  const all = model.assetSections.flatMap((s) => s.items)

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
    store.set(ASSETS_MORE_STORAGE_KEY, 'yes')
    expect(readAssetsMoreOpen(storage)).toBe(false)
  })

  it('写入后可读回；"1" 视为展开', () => {
    const store = new Map<string, string>()
    const storage = {
      getItem: (k: string) => store.get(k) ?? null,
      setItem: (k: string, v: string) => void store.set(k, v),
    }
    writeAssetsMoreOpen(storage, true)
    expect(store.get(ASSETS_MORE_STORAGE_KEY)).toBe('1')
    expect(readAssetsMoreOpen(storage)).toBe(true)
    writeAssetsMoreOpen(storage, false)
    expect(store.get(ASSETS_MORE_STORAGE_KEY)).toBe('0')
    expect(readAssetsMoreOpen(storage)).toBe(false)
  })
})
