export type SmokeEnvironment = Record<string, string | undefined>

export interface ProductionSmokeRuntime {
  baseUrl: URL
  allowedHosts: ReadonlySet<string>
  expectedBusinessText: string
  owner: string
}

export interface AuthorizedLogin {
  username: string
  password: string
}

export interface ApiAssetObservation {
  url: string
  status: number
}

export class BlockedSmokeError extends Error {
  readonly status = 'BLOCKED' as const
  readonly code: string

  constructor(
    readonly key: string,
    readonly owner: string,
    detail: string,
  ) {
    const code = `B61-BLOCKED:${key}`
    super(`${code} owner=${owner}: ${detail}`)
    this.name = 'BlockedSmokeError'
    this.code = code
  }
}

function ownerFrom(environment: SmokeEnvironment): string {
  return environment.PROD_SMOKE_OWNER?.trim() || 'UNASSIGNED'
}

function requireValue(
  environment: SmokeEnvironment,
  key: string,
  owner: string,
): string {
  const value = environment[key]?.trim()
  if (!value) {
    throw new BlockedSmokeError(key, owner, 'required smoke input is missing')
  }
  return value
}

export function readProductionSmokeRuntime(
  environment: SmokeEnvironment = process.env,
): ProductionSmokeRuntime {
  const owner = ownerFrom(environment)
  const rawBaseUrl = requireValue(environment, 'BASE_URL', owner)
  let baseUrl: URL
  try {
    baseUrl = new URL(rawBaseUrl)
  } catch {
    throw new BlockedSmokeError('BASE_URL', owner, 'expected an absolute HTTPS URL')
  }
  if (baseUrl.protocol !== 'https:') {
    throw new BlockedSmokeError('BASE_URL', owner, 'only HTTPS targets are accepted')
  }

  const allowedHosts = new Set(
    requireValue(environment, 'PROD_ALLOWED_HOSTS', owner)
      .split(',')
      .map((host) => host.trim().toLowerCase())
      .filter(Boolean),
  )
  if (!allowedHosts.has(baseUrl.hostname.toLowerCase())) {
    throw new BlockedSmokeError(
      'PROD_ALLOWED_HOSTS',
      owner,
      'base URL host is not explicitly allowlisted',
    )
  }

  return {
    baseUrl,
    allowedHosts,
    expectedBusinessText: requireValue(
      environment,
      'PROD_EXPECTED_BUSINESS_TEXT',
      owner,
    ),
    owner,
  }
}

export function readAuthorizedLogin(
  environment: SmokeEnvironment = process.env,
): AuthorizedLogin {
  const owner = ownerFrom(environment)
  if (environment.PROD_LOGIN_AUTHORIZED?.trim().toLowerCase() !== 'true') {
    throw new BlockedSmokeError(
      'PROD_LOGIN_AUTHORIZED',
      owner,
      'production login requires explicit authorization',
    )
  }
  return {
    username: requireValue(environment, 'PROD_PHONE', owner),
    password: requireValue(environment, 'PROD_PASSWORD', owner),
  }
}

export function assertApiAssetsObserved(
  observations: readonly ApiAssetObservation[],
): void {
  if (!observations.some(({ status }) => status >= 200 && status < 300)) {
    throw new Error('Production smoke observed no successful core API asset')
  }
}

export function assertProductionRequestAllowed(
  runtime: ProductionSmokeRuntime,
  rawUrl: string,
  method: string,
  allowWrite = false,
): void {
  const url = new URL(rawUrl)
  if (!runtime.allowedHosts.has(url.hostname.toLowerCase())) {
    throw new BlockedSmokeError(
      'PROD_REQUEST_HOST',
      runtime.owner,
      `${url.hostname || 'UNKNOWN'} is not allowlisted`,
    )
  }

  const normalizedMethod = method.trim().toUpperCase()
  if (!allowWrite && normalizedMethod !== 'GET' && normalizedMethod !== 'HEAD') {
    throw new BlockedSmokeError(
      'PROD_WRITE_METHOD',
      runtime.owner,
      `${normalizedMethod || 'UNKNOWN'} is not allowed in read-only smoke`,
    )
  }
}

export function assertAuthenticatedSession(
  authenticated: boolean,
  loginError: string,
): void {
  if (loginError.trim()) {
    throw new Error('Production login rejected by the target application')
  }
  if (!authenticated) {
    throw new Error('Production authenticated session marker did not appear')
  }
}
