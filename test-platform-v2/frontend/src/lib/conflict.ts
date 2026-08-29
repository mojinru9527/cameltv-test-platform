/**
 * V30-107：识别乐观锁/状态冲突（HTTP 409）。
 *
 * aitdeV2 的 HTTP 错误分支保留原始 axios error（err.response.status），
 * 业务信封错误则把后端业务码放在 err.code 上。两处都可能表达 409。
 */
export function isConflictError(err: unknown): boolean {
  if (!err || typeof err !== 'object') return false
  const e = err as {
    code?: unknown
    status?: unknown
    response?: { status?: unknown }
  }
  if (e.response?.status === 409) return true
  if (e.status === 409) return true
  if (e.code === 409) return true
  return false
}
