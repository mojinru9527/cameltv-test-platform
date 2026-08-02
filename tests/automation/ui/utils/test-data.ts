import { BlockedRunError, type RuntimeEnvironment } from './preconditions'

export type SportsTestData = Record<string, unknown>

function dataOwner(environment: RuntimeEnvironment): string {
  return environment.CAMELTV_DATA_OWNER?.trim() || 'UNASSIGNED'
}

function isSensitiveKey(key: string): boolean {
  const normalized = key.toLowerCase().replace(/[^a-z0-9]/g, '')
  return [
    'authorization',
    'cookie',
    'credential',
    'password',
    'passwd',
    'secret',
    'apikey',
    'token',
    'jwt',
  ].some((candidate) => normalized.includes(candidate))
}

function assertNoSensitiveFields(value: unknown, owner: string): void {
  if (Array.isArray(value)) {
    for (const item of value) assertNoSensitiveFields(item, owner)
    return
  }
  if (!value || typeof value !== 'object') return

  for (const [key, nestedValue] of Object.entries(value)) {
    if (isSensitiveKey(key)) {
      throw new BlockedRunError(
        'TEST_DATA_SENSITIVE_FIELD',
        owner,
        'credential-bearing fields are forbidden in the data manifest',
      )
    }
    assertNoSensitiveFields(nestedValue, owner)
  }
}

export function loadTestData(
  environment: RuntimeEnvironment = process.env,
): SportsTestData {
  const owner = dataOwner(environment)
  const raw = environment.CAMELTV_TEST_DATA_JSON?.trim()
  if (!raw) {
    throw new BlockedRunError(
      'CAMELTV_TEST_DATA_JSON',
      owner,
      'stable sports data manifest is missing',
    )
  }

  let parsed: unknown
  try {
    parsed = JSON.parse(raw)
  } catch {
    throw new BlockedRunError(
      'CAMELTV_TEST_DATA_JSON',
      owner,
      'stable sports data manifest is not valid JSON',
    )
  }
  if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
    throw new BlockedRunError(
      'CAMELTV_TEST_DATA_JSON',
      owner,
      'stable sports data manifest must be a JSON object',
    )
  }

  assertNoSensitiveFields(parsed, owner)
  return parsed as SportsTestData
}

export function requireTestData(
  data: SportsTestData,
  path: string,
  owner = 'UNASSIGNED',
): unknown {
  const value = path.split('.').reduce<unknown>((current, segment) => {
    if (!current || typeof current !== 'object' || Array.isArray(current)) {
      return undefined
    }
    return (current as Record<string, unknown>)[segment]
  }, data)

  if (value === undefined || value === null || value === '') {
    throw new BlockedRunError(
      `DATA:${path}`,
      owner,
      'required stable business key is missing',
    )
  }
  return value
}
