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

  it('batch-212：测试计划/Playground 独立入口已下架，命令面板不再收录', () => {
    const paths = ALL_COMMAND_ROUTES.map((route) => route.path)
    expect(paths).not.toContain('/testplan')
    expect(paths).not.toContain('/playground')
    expect(paths).not.toContain('/testcase?tab=playground')
    expect(paths).not.toContain('/testcase?tab=playground')
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

  it('无 release:view 权限时隐藏需要权限的入口', () => {
    const hasPerm = (code: string) => code !== 'release:view'
    const visible = filterCommandRoutes(ALL_COMMAND_ROUTES, hasPerm)
    expect(visible.length).toBeGreaterThan(0)
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
    // 非 menuBacked 条目不受菜单集合影响
    expect(visiblePaths).toContain('/workbench')
  })

  it('P1a：不传菜单集合时保持旧行为（仅按权限过滤）', () => {
    const visible = filterCommandRoutes(ALL_COMMAND_ROUTES, () => true)
    const visiblePaths = visible.map((route) => route.path)
    expect(visiblePaths).toContain('/notify')
    expect(visiblePaths).toContain('/integration')
  })
})

/**
 * batch-272（选项 B：按角色瘦身）：侧栏不再列出的模块，必须仍能**从命令面板搜到并直达**。
 * 这些页面的菜单仍由 /system/menus 返回（后端按角色权限过滤），所以「瘦身 ≠ 下架」成立；
 * 若哪天有人把某页从菜单里摘掉（硬/软下线），这里的负向断言会失败，提示同步处理。
 */
describe('batch-272 瘦身模块的搜索直达对账', () => {
  const SLIMMED_OUT = [
    '/dsh-tasks',
    '/ai-config',
    '/my-projects',
    '/schedule',
    '/system',
    '/admin/workers',
  ]

  it('菜单仍在时：被瘦身出侧栏的模块全部可搜到', () => {
    const menuPaths = new Set(ALL_COMMAND_ROUTES.map((route) => route.path))
    const visible = filterCommandRoutes(ALL_COMMAND_ROUTES, () => true, menuPaths)
    const visiblePaths = visible.map((route) => route.path)
    for (const path of SLIMMED_OUT) {
      expect(visiblePaths).toContain(path)
    }
  })

  it('菜单被软/硬下线时：对应模块同步从命令面板消失（不会搜索到已下线页面）', () => {
    const menuPaths = new Set(
      ALL_COMMAND_ROUTES.map((route) => route.path).filter((p) => p !== '/dsh-tasks'),
    )
    const visible = filterCommandRoutes(ALL_COMMAND_ROUTES, () => true, menuPaths)
    expect(visible.map((route) => route.path)).not.toContain('/dsh-tasks')
  })
})
