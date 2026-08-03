import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const { authState } = vi.hoisted(() => ({
  authState: {
    token: 'jwt-token' as string | null,
    currentProjectId: 7 as number | null,
  },
}))

vi.mock('@/stores/auth', () => ({
  useAuthStore: {
    getState: () => authState,
  },
}))

import { downloadExport, exportExcelUrl, importExcel, importXmind } from '../testcase'
import api from '../client'

describe('testcase import/export（batch-70）', () => {
  beforeEach(() => {
    authState.token = 'jwt-token'
    authState.currentProjectId = 7
    vi.spyOn(api, 'post').mockResolvedValue({ imported: 3, total: 3 })
    vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:batch70')
    vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => {})
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('exportExcelUrl builds /export/excel with filters', () => {
    expect(exportExcelUrl({ domain: '用户端' })).toContain('/test-cases/export/excel?domain=')
  })

  it('importExcel posts multipart to /import/excel', async () => {
    const file = new File(['x'], 'cases.xlsx')
    await importExcel(file)
    expect(api.post).toHaveBeenCalledWith(
      '/test-cases/import/excel',
      expect.any(FormData),
      expect.objectContaining({ headers: { 'Content-Type': 'multipart/form-data' } }),
    )
  })

  it('importXmind posts multipart to /import/xmind', async () => {
    const file = new File(['x'], 'cases.xmind')
    await importXmind(file)
    expect(api.post).toHaveBeenCalledWith(
      '/test-cases/import/xmind',
      expect.any(FormData),
      expect.objectContaining({ headers: { 'Content-Type': 'multipart/form-data' } }),
    )
  })

  it('downloadExport fetches blob with auth headers', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response('xlsx', {
      status: 200,
      headers: { 'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' },
    }))
    await downloadExport('excel', { domain: '用户端' })
    const [url, options] = fetchMock.mock.calls[0]
    expect(String(url)).toContain('/test-cases/export/excel')
    expect(options).toMatchObject({
      credentials: 'include',
      headers: { Authorization: 'Bearer jwt-token', 'X-Project-Id': '7' },
    })
  })
})
