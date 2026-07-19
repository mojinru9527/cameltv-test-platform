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
  const candidates = lineItems.length > 1
    ? lineItems
    : text.split(/(?=\d+\s*[、.．)）])/g).map((item) => item.trim()).filter(Boolean)
  const items = candidates.length > 1
    ? candidates
    : text.split(/[；;]/).map((item) => item.trim()).filter(Boolean)
  return items.map((item) => item.replace(NUMBER_PREFIX, '').trim()).filter(Boolean)
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
