#!/usr/bin/env node
/**
 * Fail-closed ratchet for the complete frontend npm audit.
 *
 * Production dependencies are already a hard zero-vulnerability gate. This
 * script covers dev/transitive tooling as well: existing advisories are pinned
 * by package/severity/advisory identity, while any new advisory fails CI.
 */
import { spawnSync } from 'node:child_process'
import { existsSync, readFileSync, writeFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const repoRoot = resolve(dirname(fileURLToPath(import.meta.url)), '../..')
const frontendRoot = resolve(repoRoot, 'test-platform-v2/frontend')
const baselinePath = resolve(frontendRoot, 'npm-audit-baseline.json')
const auditArgs = ['audit', '--json', '--registry=https://registry.npmjs.org']
const command = process.platform === 'win32' ? (process.env.ComSpec || 'cmd.exe') : 'npm'
const commandArgs = process.platform === 'win32'
  ? ['/d', '/s', '/c', `npm ${auditArgs.join(' ')}`]
  : auditArgs

const result = spawnSync(
  command,
  commandArgs,
  { cwd: frontendRoot, encoding: 'utf8', maxBuffer: 20 * 1024 * 1024 },
)

if (!result.stdout) {
  console.error(result.stderr || 'npm audit produced no JSON output')
  process.exit(1)
}

let audit
try {
  audit = JSON.parse(result.stdout)
} catch (error) {
  console.error(`Unable to parse npm audit JSON: ${error.message}`)
  process.exit(1)
}

function advisoryKeys() {
  const keys = []
  for (const [name, vulnerability] of Object.entries(audit.vulnerabilities ?? {})) {
    const severity = vulnerability.severity ?? 'unknown'
    const viaEntries = Array.isArray(vulnerability.via) ? vulnerability.via : [vulnerability.via]
    for (const via of viaEntries) {
      if (typeof via === 'string') {
        keys.push(`${name}|${severity}|via:${via}`)
      } else if (via && typeof via === 'object') {
        keys.push(`${name}|${severity}|${via.source ?? ''}|${via.name ?? ''}|${via.title ?? ''}`)
      }
    }
    if (viaEntries.length === 0) keys.push(`${name}|${severity}|unknown`)
  }
  return [...new Set(keys)].sort()
}

const advisories = advisoryKeys()
const counts = audit.metadata?.vulnerabilities ?? {}

if (process.argv.includes('--update')) {
  writeFileSync(
    baselinePath,
    `${JSON.stringify({
      schema_version: 1,
      generated_at: new Date().toISOString(),
      policy: 'full npm audit ratchet; production audit must still be zero',
      counts,
      advisories,
    }, null, 2)}\n`,
    'utf8',
  )
  console.log(`updated ${baselinePath}: advisories=${advisories.length}`)
  process.exit(0)
}

if (!existsSync(baselinePath)) {
  console.error(`baseline missing: ${baselinePath}; run with --update`)
  process.exit(1)
}

const baseline = JSON.parse(readFileSync(baselinePath, 'utf8'))
const baselineSet = new Set(baseline.advisories ?? [])
const newAdvisories = advisories.filter((key) => !baselineSet.has(key))
const removed = [...baselineSet].filter((key) => !advisories.includes(key))

console.log(
  `npm audit ratchet: baseline=${baselineSet.size} current=${advisories.length} new=${newAdvisories.length} removed=${removed.length}`,
)
console.log(`severity counts: ${JSON.stringify(counts)}`)

if (newAdvisories.length > 0) {
  console.error('new npm audit advisories:')
  for (const advisory of newAdvisories) console.error(`  ${advisory}`)
  process.exit(1)
}

console.log('NPM_AUDIT_RATCHET=PASS')
