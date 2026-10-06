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
        // 传递依赖：只按「包名 + 传递来源包名」定键（两者都稳定）。
        keys.push(`${name}|via:${via}`)
      } else if (via && typeof via === 'object') {
        // 直接公告：**只用公告身份定键**（source 为 npm advisory ID，最稳定；
        // 缺失时退回 url / title），刻意**不把 severity 与 title 放进键**。
        //
        // 原因（本批实测的随机失败）：上游会在事后**重分类严重级别**或微调标题，
        // 而这些字段一旦进键，同一处历史问题就会被判成「新增」。Batch 273 实测：
        // 本机刷新基线后约 20 分钟，CI 即报 `baseline=42 current=42 new=1 removed=1`
        // ——总数未变（27），只是其中一条由 high 被上游改判为 moderate。
        // 这会让**任何** PR 随机失败，与改动无关。
        // 去掉这两个易变字段后，门禁仍然拦得住「真正新出现的公告」，但不再被
        // 上游的重分类/改写误伤；severity 仍通过下方 counts 输出保留可观测性。
        const identity = via.source ?? via.url ?? via.title ?? ''
        keys.push(`${name}|${identity}`)
      }
    }
    if (viaEntries.length === 0) keys.push(`${name}|unknown`)
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
