type ApiErrorBody = {
  msg?: unknown
  detail?: unknown
}

function nonEmptyString(value: unknown): string | null {
  return typeof value === 'string' && value.trim() ? value : null
}

function structuredDetailMessage(detail: Record<string, unknown>): string | null {
  return (
    nonEmptyString(detail.message) ??
    nonEmptyString(detail.msg) ??
    nonEmptyString(detail.error)
  )
}

export function normalizeApiErrorMessage(body: unknown, fallback: unknown): string {
  const payload = body && typeof body === 'object' ? (body as ApiErrorBody) : undefined
  const envelopeMessage = nonEmptyString(payload?.msg)
  if (envelopeMessage) return envelopeMessage

  const detail = payload?.detail
  if (Array.isArray(detail)) {
    const parts = detail
      .map((item) => {
        if (!item || typeof item !== 'object') return nonEmptyString(item)
        const record = item as Record<string, unknown>
        const location = Array.isArray(record.loc) ? record.loc.at(-1) : null
        const field = typeof location === 'string' || typeof location === 'number'
          ? String(location)
          : ''
        const message = nonEmptyString(record.msg) ?? nonEmptyString(record.message) ?? ''
        return [field, message].filter(Boolean).join(': ') || null
      })
      .filter((part): part is string => Boolean(part))
    if (parts.length > 0) return `请求参数校验失败：${parts.join('; ')}`
  }

  const detailMessage = nonEmptyString(detail)
  if (detailMessage) return detailMessage
  if (detail && typeof detail === 'object') {
    const structuredMessage = structuredDetailMessage(detail as Record<string, unknown>)
    if (structuredMessage) return structuredMessage
  }

  return nonEmptyString(fallback) ?? '网络错误'
}
