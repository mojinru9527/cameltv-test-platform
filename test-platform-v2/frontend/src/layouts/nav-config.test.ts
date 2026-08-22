import { describe, expect, it } from 'vitest'

import type { MenuItem } from '@/types'
import {
  MORE_MENUS_STORAGE_KEY,
  PRIMARY_MENU_CODES,
  isPathInMenus,
  readMoreMenusOpen,
  splitMenusByFrequency,
  writeMoreMenusOpen,
} from './nav-config'

function menu(code: string, path: string): MenuItem {
  return { code, name: code, path, icon: '', sort: 0 }
}

// 与生产菜单目录一致的 18 个一级菜单（c165-3 基线）
const ALL_MENUS: MenuItem[] = [
  menu('menu:workbench', '/workbench'),
  menu('menu:requirement', '/requirement'),
  menu('menu:versionmission', '/release-bundles'),
  menu('menu:knowledge', '/knowledge'),
  menu('menu:testcase', '/testcase'),
  menu('menu:testplan', '/testplan'),
  menu('menu:apitest', '/apitest'),
  menu('menu:uitest', '/uitest'),
  menu('menu:schedule', '/schedule'),
  menu('menu:report', '/report'),
  menu('menu:system', '/system'),
  menu('menu:myproject', '/my-projects'),
  menu('menu:defect', '/defect'),
  menu('menu:dataset', '/dataset'),
  menu('menu:environment', '/environment'),
  menu('menu:dsh_tasks', '/dsh-tasks'),
  menu('menu:lanhu_evidence', '/lanhu-evidence'),
  menu('menu:ai_config', '/ai-config'),
]

describe('c165-3 导航频率分层 splitMenusByFrequency', () => {
  it('9 个高频 code 归位 primary，其余 9 个落入 more', () => {
    const { primary, more } = splitMenusByFrequency(ALL_MENUS)
    expect(primary).toHaveLength(9)
    expect(more).toHaveLength(9)
    for (const item of primary) {
      expect(PRIMARY_MENU_CODES.has(item.code)).toBe(true)
    }
    expect(more.map((m) => m.code)).toEqual([
      'menu:versionmission',
      'menu:testplan',
      'menu:report',
      'menu:system',
      'menu:myproject',
      'menu:defect',
      'menu:dataset',
      'menu:environment',
      'menu:lanhu_evidence',
    ])
  })

  it('fail-safe：未知新 code 一律落入 more，不污染高频区', () => {
    const { primary, more } = splitMenusByFrequency([menu('menu:future_feature', '/future')])
    expect(primary).toHaveLength(0)
    expect(more.map((m) => m.code)).toEqual(['menu:future_feature'])
  })

  it('空输入安全', () => {
    const { primary, more } = splitMenusByFrequency([])
    expect(primary).toEqual([])
    expect(more).toEqual([])
  })
})

describe('c165-3 isPathInMenus（活跃自动展开判定）', () => {
  const MORE = splitMenusByFrequency(ALL_MENUS).more

  it('命中组内菜单路径（含子路径）', () => {
    expect(isPathInMenus('/report', MORE)).toBe(true)
    expect(isPathInMenus('/report/123', MORE)).toBe(true)
    expect(isPathInMenus('/defect', MORE)).toBe(true)
  })

  it('高频区路径不命中 more 组', () => {
    expect(isPathInMenus('/workbench', MORE)).toBe(false)
    expect(isPathInMenus('/testcase', MORE)).toBe(false)
  })

  it('菜单路径的查询串不参与比较', () => {
    const withQuery = [menu('menu:knowledge', '/knowledge?tab=graph')]
    expect(isPathInMenus('/knowledge', withQuery)).toBe(true)
  })

  it('空路径菜单不造成误命中', () => {
    expect(isPathInMenus('/anything', [menu('menu:x', '')])).toBe(false)
  })
})

describe('c165-3 「更多功能」展开状态持久化', () => {
  it('默认收起（key 不存在 / 非 "1" 均为收起）', () => {
    const store = new Map<string, string>()
    const storage = { getItem: (k: string) => store.get(k) ?? null }
    expect(readMoreMenusOpen(storage)).toBe(false)
    store.set(MORE_MENUS_STORAGE_KEY, 'yes')
    expect(readMoreMenusOpen(storage)).toBe(false)
  })

  it('写入后可读回；"1" 视为展开', () => {
    const store = new Map<string, string>()
    const storage = {
      getItem: (k: string) => store.get(k) ?? null,
      setItem: (k: string, v: string) => void store.set(k, v),
    }
    writeMoreMenusOpen(storage, true)
    expect(store.get(MORE_MENUS_STORAGE_KEY)).toBe('1')
    expect(readMoreMenusOpen(storage)).toBe(true)
    writeMoreMenusOpen(storage, false)
    expect(store.get(MORE_MENUS_STORAGE_KEY)).toBe('0')
    expect(readMoreMenusOpen(storage)).toBe(false)
  })
})
