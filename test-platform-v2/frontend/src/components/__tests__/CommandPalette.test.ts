import { describe, expect, it } from 'vitest'

import {
  ALL_COMMAND_ROUTES,
  filterCommandRoutes,
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
      '/report?tab=trace',
      '/testcase?tab=mindmap',
      '/release-bundles',
      '/knowledge',
      '/dataset',
      '/integration',
      '/environment',
      '/notify',
      '/my-projects',
      '/system',
      '/apitest',
      '/uitest',
    ]) {
      expect(paths).toContain(expected)
    }
  })

  it('P1b：Agent 工作台已收敛进 DSH 任务，入口不再单列', () => {
    const paths = ALL_COMMAND_ROUTES.map((route) => route.path)
    expect(paths).not.toContain('/agent-workbench')
  })

  it('P2a：思维导图并入用例服务脑图视图 Tab，旧独立路径不再出现', () => {
    const paths = ALL_COMMAND_ROUTES.map((route) => route.path)
    expect(paths).not.toContain('/mindmap')
    expect(paths).toContain('/testcase?tab=mindmap')
  })

  it('P2b：Playground 并入用例服务 Tab，旧独立路径不再出现', () => {
    const paths = ALL_COMMAND_ROUTES.map((route) => route.path)
    expect(paths).not.toContain('/playground')
    expect(paths).toContain('/testcase?tab=playground')
  })

  it('P2c：质量追溯并入报告中心 Tab，旧独立路径不再出现', () => {
    const paths = ALL_COMMAND_ROUTES.map((route) => route.path)
    expect(paths).not.toContain('/trace')
    expect(paths).toContain('/report?tab=trace')
  })

  it('batch-165：专项测试/性能监控入口已隐藏', () => {
    const paths = ALL_COMMAND_ROUTES.map((route) => route.path)
    expect(paths).not.toContain('/special')
    expect(paths).not.toContain('/perftest')
    expect(paths).not.toContain('/project')
    expect(paths).not.toContain('/organizations')
    expect(paths).toContain('/my-projects')
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

  it('P1a：menuBacked 入口随菜单软下线隐藏（DISABLED_MENUS）', () => {
    // 模拟菜单中已不含 notify/integration（后端 DISABLED_MENUS 默认隐藏）
    const menuPaths = new Set(
      ALL_COMMAND_ROUTES.map((route) => route.path).filter((p) => p !== '/notify' && p !== '/integration'),
    )
    const visible = filterCommandRoutes(ALL_COMMAND_ROUTES, () => true, menuPaths)
    const visiblePaths = visible.map((route) => route.path)
    expect(visiblePaths).not.toContain('/notify')
    expect(visiblePaths).not.toContain('/integration')
    // 非 menuBacked 条目（如运维发布）不受菜单集合影响
    expect(visiblePaths).toContain('/operations-release')
  })

  it('P1a：不传菜单集合时保持旧行为（仅按权限过滤）', () => {
    const visible = filterCommandRoutes(ALL_COMMAND_ROUTES, () => true)
    const visiblePaths = visible.map((route) => route.path)
    expect(visiblePaths).toContain('/notify')
    expect(visiblePaths).toContain('/integration')
  })
})
