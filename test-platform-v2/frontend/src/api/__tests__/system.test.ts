import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const { authState } = vi.hoisted(() => ({
  authState: {
    token: null as string | null,
    currentProjectId: 7 as number | null,
  },
}))

vi.mock('@/stores/auth', () => ({
  useAuthStore: {
    getState: () => authState,
  },
}))

import { exportAuditLogsCsv } from '../system'

describe('exportAuditLogsCsv', () => {
  beforeEach(() => {
    authState.token = null
    authState.currentProjectId = 7
    vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:batch60-audit')
    vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => {})
    vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('uses the httpOnly cookie session and current project for binary export', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response('id,action\n1,project:update', {
      status: 200,
      headers: { 'Content-Disposition': 'attachment; filename="audit.csv"' },
    }))

    await exportAuditLogsCsv({ action: 'project:update', keyword: 'batch60' })

    expect(fetchMock).toHaveBeenCalledOnce()
    const [url, options] = fetchMock.mock.calls[0]
    expect(String(url)).toContain('action=project%3Aupdate')
    expect(String(url)).toContain('keyword=batch60')
    expect(options).toMatchObject({
      credentials: 'include',
      headers: { 'X-Project-Id': '7' },
    })
    expect((options?.headers as Record<string, string>).Authorization).toBeUndefined()
  })
})
