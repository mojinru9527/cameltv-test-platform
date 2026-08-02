export type SportsTargetEnvironment = 'test5' | 'production'
export type SportsRunLevel = 'readonly' | 'write-authorized'
export type RuntimeEnvironment = Record<string, string | undefined>

export interface RuntimePreconditions {
  targetEnvironment: SportsTargetEnvironment
  baseUrl: URL
  runLevel: SportsRunLevel
  allowedHosts: ReadonlySet<string>
  owner: string
}

export class BlockedRunError extends Error {
  readonly status = 'BLOCKED' as const
  readonly code: string

  constructor(
    readonly key: string,
    readonly owner: string,
    detail: string,
  ) {
    const code = `B61-BLOCKED:${key}`
    super(`${code} owner=${owner}: ${detail}`)
    this.name = 'BlockedRunError'
    this.code = code
  }
}

function ownerFrom(environment: RuntimeEnvironment): string {
  return environment.CAMELTV_PRECONDITION_OWNER?.trim() || 'UNASSIGNED'
}

function requiredValue(
  environment: RuntimeEnvironment,
  key: string,
  owner: string,
): string {
  const value = environment[key]?.trim()
  if (!value) {
    throw new BlockedRunError(key, owner, 'required runtime value is missing')
  }
  return value
}

export function parseRuntimePreconditions(
  environment: RuntimeEnvironment = process.env,
): RuntimePreconditions {
  const owner = ownerFrom(environment)
  const targetValue = requiredValue(environment, 'CAMELTV_TARGET_ENV', owner)
  if (targetValue !== 'test5' && targetValue !== 'production') {
    throw new BlockedRunError(
      'CAMELTV_TARGET_ENV',
      owner,
      'expected test5 or production',
    )
  }

  const baseUrlValue = requiredValue(environment, 'CAMELTV_BASE_URL', owner)
  let baseUrl: URL
  try {
    baseUrl = new URL(baseUrlValue)
  } catch {
    throw new BlockedRunError(
      'CAMELTV_BASE_URL',
      owner,
      'expected an absolute HTTPS URL',
    )
  }
  if (baseUrl.protocol !== 'https:') {
    throw new BlockedRunError(
      'CAMELTV_BASE_URL',
      owner,
      'only HTTPS targets are accepted',
    )
  }

  const runLevelValue = requiredValue(environment, 'CAMELTV_RUN_LEVEL', owner)
  if (runLevelValue !== 'readonly' && runLevelValue !== 'write-authorized') {
    throw new BlockedRunError(
      'CAMELTV_RUN_LEVEL',
      owner,
      'expected readonly or write-authorized',
    )
  }

  const allowedHosts = new Set(
    requiredValue(environment, 'CAMELTV_ALLOWED_HOSTS', owner)
      .split(',')
      .map((host) => host.trim().toLowerCase())
      .filter(Boolean),
  )
  if (!allowedHosts.has(baseUrl.hostname.toLowerCase())) {
    throw new BlockedRunError(
      'CAMELTV_ALLOWED_HOSTS',
      owner,
      'base URL host is not explicitly allowlisted',
    )
  }

  if (targetValue === 'production' && runLevelValue !== 'readonly') {
    throw new BlockedRunError(
      'PRODUCTION_RUN_LEVEL',
      owner,
      'production is restricted to readonly observation',
    )
  }

  return {
    targetEnvironment: targetValue,
    baseUrl,
    runLevel: runLevelValue,
    allowedHosts,
    owner,
  }
}

export function assertRequestMethodAllowed(
  preconditions: RuntimePreconditions,
  method: string,
): void {
  const normalizedMethod = method.trim().toUpperCase()
  if (normalizedMethod === 'GET' || normalizedMethod === 'HEAD') return

  if (preconditions.targetEnvironment === 'production') {
    throw new BlockedRunError(
      'PRODUCTION_WRITE_METHOD',
      preconditions.owner,
      `${normalizedMethod || 'UNKNOWN'} is not allowed for production`,
    )
  }

  if (preconditions.runLevel !== 'write-authorized') {
    throw new BlockedRunError(
      'READONLY_WRITE_METHOD',
      preconditions.owner,
      `${normalizedMethod || 'UNKNOWN'} requires explicit write authorization`,
    )
  }
}

export function assertNetworkRequestAllowed(
  preconditions: RuntimePreconditions,
  rawUrl: string,
  method: string,
): void {
  let url: URL
  try {
    url = new URL(rawUrl)
  } catch {
    throw new BlockedRunError(
      'REQUEST_URL',
      preconditions.owner,
      'browser request URL is not absolute',
    )
  }

  if (!preconditions.allowedHosts.has(url.hostname.toLowerCase())) {
    throw new BlockedRunError(
      'REQUEST_HOST',
      preconditions.owner,
      `${url.hostname || 'UNKNOWN'} is not allowlisted`,
    )
  }

  if (preconditions.targetEnvironment === 'production') {
    assertRequestMethodAllowed(preconditions, method)
  }
}
