import { describe, expect, it } from 'vitest'

import { resolveGuestModule } from './guestModuleCatalog'

const PUBLIC_MODULE_PATHS = [
  '/workbench',
  '/trace',
  '/requirement',
  '/release-bundles',
  '/knowledge',
  '/mindmap',
  '/testcase',
  '/testplan',
  '/apitest',
  '/uitest',
  '/playground',
  '/schedule',
  '/report',
  '/system',
  '/my-projects',
  '/defect',
  '/dataset',
  '/integration',
  '/notify',
  '/environment',
  // (P1b) '/agent-workbench' 已收敛进 DSH 任务，访客目录不再单列
  '/lanhu-evidence',
] as const

describe('访客模块能力目录', () => {
  it.each(PUBLIC_MODULE_PATHS)('%s 有可供注册前评估的完整说明', (path) => {
    const module = resolveGuestModule(path)

    expect(module.title.trim()).not.toBe('')
    expect(module.description.trim()).not.toBe('')
    expect(module.capabilities.length).toBeGreaterThanOrEqual(3)
    expect(module.capabilities.every((item) => item.title && item.description)).toBe(true)
  })

  it('未知路径使用安全说明且不虚构业务数据', () => {
    const module = resolveGuestModule('/future-capability', '', '未来能力')

    expect(module.title).toBe('未来能力')
    expect(module.description).toContain('登录')
    expect(module.capabilities.length).toBeGreaterThanOrEqual(3)
  })
})
