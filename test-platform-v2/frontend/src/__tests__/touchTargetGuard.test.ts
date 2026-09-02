import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

/**
 * B60-P2-002：关键操作按钮必须提供 ≥44px（min-h-11）触控目标。
 * 以源码断言守护，防止回归时悄悄缩小命中区。
 */
const PAGES = [
  'src/pages/report/index.tsx',
  'src/pages/schedule/index.tsx',
  'src/pages/notify/index.tsx',
  'src/pages/environment/index.tsx',
  'src/pages/dataset/index.tsx',
] as const

describe('移动端触控目标守护（B60-P2-002）', () => {
  PAGES.forEach((page) => {
    it(`${page} 包含 min-h-11 触控目标`, () => {
      const source = readFileSync(resolve(process.cwd(), page), 'utf-8')
      expect(source).toContain('min-h-11')
    })
  })
})



