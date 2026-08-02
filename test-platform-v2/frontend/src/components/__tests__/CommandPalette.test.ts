import { describe, expect, it } from 'vitest'

import {
  ALL_COMMAND_ROUTES,
  filterCommandRoutes,
  type CommandRoute,
} from '../CommandPalette'

describe('CommandPalette 路由对账（B60-P1-002）', () => {
  it('覆盖全部成熟模块路由', () => {
    const paths = ALL_COMMAND_ROUTES.map((route) => route.path)
    for (const expected of [
      '/workbench',
      '/testcase',
      '/testplan',
      '/requirement',
      '/report',
      '/schedule',
      '/defect',
      '/trace',
      '/mindmap',
      '/release-bundles',
      '/knowledge',
      '/dataset',
      '/integration',
      '/environment',
      '/notify',
      '/project',
      '/system',
      '/apitest',
      '/uitest',
      '/special',
      '/agent-workbench',
      '/perftest',
    ]) {
      expect(paths).toContain(expected)
    }
  })

  it('无 release:view 权限时隐藏运维发布入口', () => {
    const hasPerm = (code: string) => code !== 'release:view'
    const visible = filterCommandRoutes(ALL_COMMAND_ROUTES, hasPerm)
    expect(visible.some((route) => route.path === '/operations-release')).toBe(false)
    expect(visible.some((route) => route.path === '/workbench')).toBe(true)
  })

  it('超级权限可见全部入口', () => {
    const visible = filterCommandRoutes(ALL_COMMAND_ROUTES, () => true)
    expect(visible).toHaveLength(ALL_COMMAND_ROUTES.length)
  })
})
