import type { MenuItem } from '@/types'

/**
 * (c165-3 导航频率分层) 高频一级菜单 code 集合——产品负责人按团队使用频率确认。
 * 侧边栏默认只平铺这些入口；其余一级菜单收进「更多功能」折叠组。
 * 调整某个入口的归属 = 增删本集合中的一行。
 */
export const PRIMARY_MENU_CODES: ReadonlySet<string> = new Set([
  'menu:workbench',
  // V4.0 AITDE 主链（Mission→Contract→Scenario→Run）是本版本的核心入口。
  // P2-9：此前它落在 fail-safe 的「更多功能」折叠组，且排在 11 项的第 10 位，
  // 黑盒测试中需展开折叠组才能发现，旗舰功能可发现性不合格。
  'menu:missions',
  'menu:requirement',
  'menu:knowledge',
  'menu:testcase',
  'menu:apitest',
  'menu:uitest',
  'menu:schedule',
  'menu:dsh_tasks',
  'menu:ai_config',
])

/** 「更多功能」折叠组展开状态的 localStorage key（"1"=展开，其余/缺省=收起）。 */
export const MORE_MENUS_STORAGE_KEY = 'sidebar:more-menus-open'

export interface MenuFrequencySplit {
  primary: MenuItem[]
  more: MenuItem[]
}

/**
 * 按使用频率把一级菜单拆为高频平铺区与「更多功能」折叠组。
 * fail-safe：不在 PRIMARY_MENU_CODES 中的 code（含未来新增菜单）一律落入 more，
 * 以后新功能上线不会污染高频区。
 */
export function splitMenusByFrequency(menus: MenuItem[]): MenuFrequencySplit {
  const primary: MenuItem[] = []
  const more: MenuItem[] = []
  for (const menu of menus) {
    if (PRIMARY_MENU_CODES.has(menu.code)) primary.push(menu)
    else more.push(menu)
  }
  return { primary, more }
}

/**
 * 当前路径是否命中给定菜单组内的任一项（命中时「更多功能」自动展开，
 * 避免活跃导航项被折叠隐藏）。菜单路径的查询串不参与比较。
 */
export function isPathInMenus(pathname: string, menus: MenuItem[]): boolean {
  return menus.some((menu) => {
    const base = menu.path.split('?')[0]
    return base !== '' && (pathname === base || (base !== '/' && pathname.startsWith(base)))
  })
}

/** 读取「更多功能」持久化展开状态（默认收起）。 */
export function readMoreMenusOpen(storage: Pick<Storage, 'getItem'>): boolean {
  return storage.getItem(MORE_MENUS_STORAGE_KEY) === '1'
}

/** 持久化「更多功能」展开状态。 */
export function writeMoreMenusOpen(storage: Pick<Storage, 'setItem'>, open: boolean): void {
  storage.setItem(MORE_MENUS_STORAGE_KEY, open ? '1' : '0')
}
