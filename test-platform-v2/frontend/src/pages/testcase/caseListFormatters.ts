type StepRecord = Record<string, unknown>

const NUMBER_PREFIX = /^\s*\d+\s*[、.．)）:：-]\s*/

function toDisplayText(value: unknown): string {
  if (typeof value === 'string' || typeof value === 'number') return String(value).trim()
  if (!value || typeof value !== 'object') return ''
  const item = value as StepRecord
  return String(
    item.desc ?? item.action ?? item.description ?? item.text ?? item.expected ?? item.name ?? '',
  ).trim()
}

function parseArray(value: string): unknown[] | null {
  const text = value.trim()
  if (!text.startsWith('[')) return null
  try {
    const parsed = JSON.parse(text)
    return Array.isArray(parsed) ? parsed : null
  } catch {
    return null
  }
}

function parseLegacyStepRecords(value: string): StepRecord[] | null {
  const text = value.trim()
  if (!text.startsWith('[') || !text.endsWith(']')) return null

  const keys = ['step', 'desc', 'action', 'description', 'text', 'expected', 'expected_result', 'result', 'name']
  const keyPattern = keys.join('|')
  const records = Array.from(text.matchAll(/\{([\s\S]*?)\}/g)).map((match) => {
    const body = match[1]
    const record: StepRecord = {}
    for (const key of keys) {
      const fieldPattern = new RegExp(
        `(?:^|,)\\s*${key}\\s*:\\s*([\\s\\S]*?)(?=,\\s*(?:${keyPattern})\\s*:|$)`,
        'i',
      )
      const field = body.match(fieldPattern)?.[1]?.trim()
      if (field) record[key] = field.replace(/^(['"])([\s\S]*)\1$/, '$2').trim()
    }
    return record
  }).filter((record) => Object.keys(record).length > 0)

  return records.length ? records : null
}

function extractItems(value: unknown): string[] {
  if (Array.isArray(value)) return value.map(toDisplayText).filter(Boolean)
  const text = toDisplayText(value)
  if (!text) return []

  const jsonItems = parseArray(text)
  if (jsonItems) return jsonItems.map(toDisplayText).filter(Boolean)

  const lineItems = text.split(/\r?\n/).map((item) => item.trim()).filter(Boolean)
  if (lineItems.length > 1) {
    return lineItems.map((item) => item.replace(NUMBER_PREFIX, '').trim()).filter(Boolean)
  }

  // Batch 174（FIX-173-P0-04）：仅当单行文本以「数字列表前缀」开头时才按
  // 分隔符拆分。此前用全局 lookahead `/(?=\d+\s*[、.．)）])/g` 会把正文中的
  // 合法数字（如「假设上限10000），创作者已登录」「latestVersion=6.0.0」）
  // 误判为列表项并拆行编号（渲染成「2、1 3、0 4、0」），大量用例内容失真。
  // 现在要求文本本身以 `1、`/`1.`/`1）` 等列表开头，正文数字不再触发拆分。
  const startsAsList = /^\s*\d+\s*[、.．)）]/.test(text)
  if (startsAsList) {
    const candidates = text.split(/(?=\d+\s*[、.．)）])/g).map((item) => item.trim()).filter(Boolean)
    if (candidates.length > 1) {
      return candidates.map((item) => item.replace(NUMBER_PREFIX, '').trim()).filter(Boolean)
    }
  }
  return text.split(/[；;]/).map((item) => item.trim()).filter(Boolean)
    .map((item) => item.replace(NUMBER_PREFIX, '').trim()).filter(Boolean)
}

function numberItems(items: string[]): string[] {
  return items.map((item, index) => `${index + 1}、${item}`)
}

function parseStepRecords(value: unknown): StepRecord[] | null {
  if (Array.isArray(value)) {
    return value.filter((item): item is StepRecord => !!item && typeof item === 'object')
  }
  if (typeof value !== 'string') return null
  const parsed = parseArray(value)
  if (!parsed) return parseLegacyStepRecords(value)
  return parsed.filter((item): item is StepRecord => !!item && typeof item === 'object')
}

export function formatNumberedText(value: unknown): string[] {
  return numberItems(extractItems(value))
}

export function formatStepActions(steps: unknown): string[] {
  const records = parseStepRecords(steps)
  if (!records?.length) return formatNumberedText(steps)
  const actions = records
    .map((step) => toDisplayText(step.desc ?? step.action ?? step.description ?? step.text))
    .filter(Boolean)
  return numberItems(actions)
}

export function formatStepsForEditor(steps: unknown): string {
  return formatStepActions(steps).join('\n')
}

export function formatStepExpectations(steps: unknown, expectedResult: unknown): string[] {
  const records = parseStepRecords(steps)
  const fallback = extractItems(expectedResult)
  if (records?.length) {
    const expectations = records.map((step, index) => (
      toDisplayText(step.expected ?? step.expected_result ?? step.result) || fallback[index] || '-'
    ))
    return numberItems(expectations)
  }
  return numberItems(fallback)
}

export function sortCasesNewestFirst<T extends { id?: number; created_at?: string | null }>(items: T[]): T[] {
  return [...items].sort((left, right) => {
    const leftTime = left.created_at ? Date.parse(left.created_at) || 0 : 0
    const rightTime = right.created_at ? Date.parse(right.created_at) || 0 : 0
    if (rightTime !== leftTime) return rightTime - leftTime
    return (right.id ?? 0) - (left.id ?? 0)
  })
}

export function countCasesByType(
  stats?: { total?: number; by_type?: Record<string, number> },
): { all: number; manual: number; api: number; ui: number } {
  return {
    all: Number.isFinite(stats?.total) ? Number(stats?.total) : 0,
    manual: Number.isFinite(stats?.by_type?.manual) ? Number(stats?.by_type?.manual) : 0,
    api: Number.isFinite(stats?.by_type?.api) ? Number(stats?.by_type?.api) : 0,
    ui: Number.isFinite(stats?.by_type?.ui) ? Number(stats?.by_type?.ui) : 0,
  }
}
