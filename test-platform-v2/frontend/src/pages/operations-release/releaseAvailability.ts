export function isReleaseControlUnavailable(error: unknown): boolean {
  if (!error || typeof error !== 'object') return false
  const candidate = error as { message?: string; response?: { status?: number } }
  return candidate.response?.status === 503
    && (candidate.message ?? '').includes('release-control state store is not configured')
}
