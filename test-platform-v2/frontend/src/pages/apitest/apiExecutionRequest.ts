export type ApiExecutionSource = 'quick' | 'asset' | 'single' | 'group' | 'batch'

export type ApiAssertionDefinition = {
  type: string
  path?: string
  key?: string
  pattern?: string
  operator?: string
  expected?: unknown
}

export type QueryParameterValue = string | number | boolean | null | Array<string | number | boolean>

export type ApiRequestDefinition = {
  method: string
  url: string
  headers: Record<string, string>
  body: string
  query_params: Record<string, QueryParameterValue>
  assertions: ApiAssertionDefinition[]
}

export type ApiExecutionRequest = {
  source: ApiExecutionSource
  environment_id: number | null
  dataset_id: number | null
  case_ids: number[]
  request: ApiRequestDefinition | null
  confirm_prod: boolean
}

type RequestDefinitionInput = {
  method: string
  url: string
  headers?: string | Record<string, unknown>
  body?: string
  queryParams?: string | Record<string, QueryParameterValue>
  assertions?: string | ApiAssertionDefinition[]
}

type BuildApiExecutionRequestInput = {
  source: ApiExecutionSource
  environmentId?: number | null
  datasetId?: number | null
  caseIds?: number[]
  request: RequestDefinitionInput | null
  confirmProd?: boolean
}

const NUMERIC_ASSERTION_TYPES = new Set(['status_code', 'response_time', 'array_length'])

function parseJson<T>(value: string | T | undefined, fallback: T, label: string): T {
  if (value === undefined) return fallback
  if (typeof value !== 'string') return value
  if (!value.trim()) return fallback
  try {
    return JSON.parse(value) as T
  } catch {
    throw new Error(`${label} must be valid JSON`)
  }
}

function normalizeAssertion(assertion: ApiAssertionDefinition): ApiAssertionDefinition {
  if (
    NUMERIC_ASSERTION_TYPES.has(assertion.type)
    && typeof assertion.expected === 'string'
    && assertion.expected.trim() !== ''
    && Number.isFinite(Number(assertion.expected))
  ) {
    return { ...assertion, expected: Number(assertion.expected) }
  }
  return { ...assertion }
}

export function buildApiExecutionRequest(input: BuildApiExecutionRequestInput): ApiExecutionRequest {
  const caseIds = [...(input.caseIds ?? [])]
  const needsRequest = input.source === 'quick' || input.source === 'asset'
  if (needsRequest && !input.request) {
    throw new Error(`${input.source} execution requires a request definition`)
  }
  if (!needsRequest && caseIds.length === 0) {
    throw new Error(`${input.source} execution requires at least one case`)
  }
  if (input.source === 'single' && caseIds.length !== 1) {
    throw new Error('single execution requires exactly one case')
  }

  const request = input.request
    ? {
        method: input.request.method.toUpperCase(),
        url: input.request.url,
        headers: Object.fromEntries(
          Object.entries(parseJson<Record<string, unknown>>(input.request.headers, {}, 'headers'))
            .map(([key, value]) => [key, String(value ?? '')]),
        ),
        body: input.request.body ?? '',
        query_params: parseJson<Record<string, QueryParameterValue>>(
          input.request.queryParams,
          {},
          'query parameters',
        ),
        assertions: parseJson<ApiAssertionDefinition[]>(
          input.request.assertions,
          [],
          'assertions',
        ).map(normalizeAssertion),
      }
    : null

  return {
    source: input.source,
    environment_id: input.environmentId ?? null,
    dataset_id: input.datasetId ?? null,
    case_ids: caseIds,
    request,
    confirm_prod: input.confirmProd ?? false,
  }
}
