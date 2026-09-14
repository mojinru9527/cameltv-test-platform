import { readFileSync, readdirSync } from 'node:fs'
import { extname, relative, resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const sourceRoot = resolve(process.cwd(), 'src')
const ignoredRoots = [
  resolve(sourceRoot, 'components/ui'),
  resolve(sourceRoot, 'ui'),
]

function collectSources(directory = sourceRoot): string[] {
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const absolutePath = resolve(directory, entry.name)
    if (entry.isDirectory()) return collectSources(absolutePath)
    return ['.ts', '.tsx'].includes(extname(entry.name)) ? [absolutePath] : []
  })
}

function isIgnored(file: string): boolean {
  return ignoredRoots.some((root) => file === root || file.startsWith(`${root}\\`))
}

describe('Batch 245 UI entry governance', () => {
  it('keeps business and test code on the @/ui public entry', () => {
    const violations = collectSources()
      .filter((file) => !isIgnored(file))
      .flatMap((file) => {
        const source = readFileSync(file, 'utf8')
        return [...source.matchAll(/from\s+['"]@\/components\/ui(?:\/[a-z0-9-]+)?['"]/g)].map((match) => {
          const line = source.slice(0, match.index).split('\n').length
          return `${relative(sourceRoot, file).replaceAll('\\', '/')}:${line}`
        })
      })

    expect(violations).toEqual([])
  })

  it('keeps Radix primitives behind the canonical UI layer', () => {
    const violations = collectSources()
      .filter((file) => !isIgnored(file))
      .flatMap((file) => {
        const source = readFileSync(file, 'utf8')
        return [...source.matchAll(/from\s+['"]@radix-ui\/[^'"]+['"]/g)].map((match) => {
          const line = source.slice(0, match.index).split('\n').length
          return `${relative(sourceRoot, file).replaceAll('\\', '/')}:${line}`
        })
      })

    expect(violations).toEqual([])
  })
})
