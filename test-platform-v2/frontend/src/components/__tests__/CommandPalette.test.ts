import { describe, expect, it } from 'vitest'

import {
  ALL_COMMAND_ROUTES,
  filterCommandRoutes,
} from '../CommandPalette'

describe('CommandPalette 路由对账（B60-P1-002）', () => {
  it('覆盖全部保留模块路由', () => {
    const paths = ALL_COMMAND_ROUTES.map((route) => route.path)
    for (const expected of [
      '/workbench',
      '/testcase',
      '/requirement',
      '/schedule',
      '/defect',
      '/testcase?tab=mindmap',
      '/release-bundles',
      '/version-tasks',
      '/knowledge',
      '/environment',
      '/my-projects',
      '/system',
      '/apitest',
      '/uitest',
      '/ai-config',
      '/lanhu-evidence',
    ]) {
      expect(paths).toContain(expected)
    }
  })

  it('平台简化批次：已删除模块入口不再出现', () => {
    const paths = ALL_COMMAND_ROUTES.map((route) => route.path)
    for (const gone of [
      '/agent-workbench',
      '/report',
      '/report?tab=trace',
      '/trace',
      '/dataset',
      '/integration',
      '/notify',
      '/dsh-tasks',
      '/missions',
      '/executions',
      '/healing',
      '/flaky',
      '/data-sources',
      '/fixtures',
      '/admin/workers',
      '/ai-suggestions',
      '/metrics',
      '/onboarding',
      '/special',
      '/perftest',
      '/project',
      '/organizations',
      '/testplan',
      '/playground',
      '/mindmap',
    ]) {
      expect(paths).not.toContain(gone)
    }
  })

  it('batch-165：专项测试/性能监控入口已隐藏', () => {
    const paths = ALL_COMMAND_ROUTES.map((route) => route.path)
    expect(paths).not.toContain('/special')
    expect(paths).not.toContain('/perftest')
    expect(paths).not.toContain('/project')
    expect(paths).not.toContain('/organizations')
    expect(paths).toContain('/my-projects')
  })

  it('无权限时隐藏需要权限的入口', () => {
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
    // 模拟菜单中已不含 ai-config（软下线示例）
    const menuPaths = new Set(
      ALL_COMMAND_ROUTES.map((route) => route.path).filter((p) => p !== '/ai-config'),
    )
    const visible = filterCommandRoutes(ALL_COMMAND_ROUTES, () => true, menuPaths)
    const visiblePaths = visible.map((route) => route.path)
    expect(visiblePaths).not.toContain('/ai-config')
    // 非 menuBacked 条目不受菜单集合影响
    expect(visiblePaths).toContain('/workbench')
  })

  it('P1a：不传菜单集合时保持旧行为（仅按权限过滤）', () => {
    const visible = filterCommandRoutes(ALL_COMMAND_ROUTES, () => true)
    expect(visible.map((route) => route.path)).toContain('/ai-config')
  })
})

/**
 * batch-272（选项 B：按角色瘦身）：侧栏不再列出的模块，必须仍能**从命令面板搜到并直达**。
 * 这些页面的菜单仍由 /system/menus 返回（后端按角色权限过滤），所以「瘦身 ≠ 下架」成立；
 * 若哪天有人把某页从菜单里摘掉（硬/软下线），这里的负向断言会失败，提示同步处理。
 */
describe('batch-272 瘦身模块的搜索直达对账', () => {
  const SLIMMED_OUT = [
    '/ai-config',
    '/my-projects',
    '/schedule',
    '/system',
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
      ALL_COMMAND_ROUTES.map((route) => route.path).filter((p) => p !== '/ai-config'),
    )
    const visible = filterCommandRoutes(ALL_COMMAND_ROUTES, () => true, menuPaths)
    expect(visible.map((route) => route.path)).not.toContain('/ai-config')
  })
})
