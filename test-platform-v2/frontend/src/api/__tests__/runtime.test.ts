/**
 * AITDE V3.4 Durable Runtime API function tests — endpoint, method, payload.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'

const mockGet = vi.fn()
const mockPost = vi.fn()

vi.mock('@/api/missions', () => ({
  aitdeV2: {
    get: (...args: any[]) => mockGet(...args),
    post: (...args: any[]) => mockPost(...args),
  },
}))

const {
  fetchWorkers,
  fetchWorker,
  drainWorker,
  disableWorker,
  fetchWorkflows,
  resumeRun,
  fetchPolicyProfiles,
  evaluatePolicy,
  fetchSecretRefs,
  createSecretRef,
  fetchApprovals,
  approveApproval,
  rejectApproval,
} = await import('@/api/runtime')

describe('runtime API functions', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Workers', () => {
    it('fetchWorkers GETs /workers', async () => {
      mockGet.mockResolvedValue({ items: [] })
      await fetchWorkers()
      expect(mockGet).toHaveBeenCalledWith('/workers', expect.objectContaining({}))
    })

    it('fetchWorker GETs /workers/:id', async () => {
      mockGet.mockResolvedValue({ id: 1 })
      await fetchWorker(1)
      expect(mockGet).toHaveBeenCalledWith('/workers/1', expect.objectContaining({}))
    })

    it('drainWorker POSTs /workers/:id/drain', async () => {
      mockPost.mockResolvedValue({ id: 1 })
      await drainWorker(1)
      expect(mockPost).toHaveBeenCalledWith('/workers/1/drain')
    })

    it('disableWorker POSTs /workers/:id/disable', async () => {
      mockPost.mockResolvedValue({ id: 1 })
      await disableWorker(1)
      expect(mockPost).toHaveBeenCalledWith('/workers/1/disable')
    })
  })

  describe('Workflows', () => {
    it('fetchWorkflows GETs /workflows with pagination', async () => {
      mockGet.mockResolvedValue({ total: 0, page: 1, page_size: 20, items: [] })
      await fetchWorkflows({ page: 2, page_size: 10 })
      expect(mockGet).toHaveBeenCalledWith(
        '/workflows',
        expect.objectContaining({ params: { page: 2, page_size: 10 } }),
      )
    })

    it('resumeRun POSTs /runs/:id/resume with workflow_id', async () => {
      mockPost.mockResolvedValue({ status: 'RESUMING' })
      await resumeRun(9, 'wf-1')
      expect(mockPost).toHaveBeenCalledWith(
        '/runs/9/resume',
        { workflow_id: 'wf-1', signal_name: 'resume', args: {} },
      )
    })
  })

  describe('Policies', () => {
    it('fetchPolicyProfiles GETs /policy-profiles', async () => {
      mockGet.mockResolvedValue({ items: [] })
      await fetchPolicyProfiles()
      expect(mockGet).toHaveBeenCalledWith('/policy-profiles', expect.objectContaining({}))
    })

    it('evaluatePolicy POSTs /policy/evaluate', async () => {
      mockPost.mockResolvedValue({ decision: 'ALLOW', reason: 'ok' })
      await evaluatePolicy({ driver: 'http', action: 'get', network_zone: 'TEST' })
      expect(mockPost).toHaveBeenCalledWith('/policy/evaluate', expect.objectContaining({ driver: 'http', action: 'get', network_zone: 'TEST' }))
    })
  })

  describe('Secret refs', () => {
    it('fetchSecretRefs GETs /secret-refs', async () => {
      mockGet.mockResolvedValue({ items: [] })
      await fetchSecretRefs()
      expect(mockGet).toHaveBeenCalledWith('/secret-refs', expect.objectContaining({}))
    })

    it('createSecretRef POSTs /secret-refs without a value', async () => {
      mockPost.mockResolvedValue({ id: 1 })
      await createSecretRef({ name: 'x', provider: 'env', external_ref: 'TOKEN' })
      expect(mockPost).toHaveBeenCalledWith('/secret-refs', expect.objectContaining({ name: 'x', provider: 'env', external_ref: 'TOKEN' }))
    })
  })

  describe('Approvals', () => {
    it('fetchApprovals GETs /approvals', async () => {
      mockGet.mockResolvedValue({ items: [] })
      await fetchApprovals()
      expect(mockGet).toHaveBeenCalledWith('/approvals', expect.objectContaining({}))
    })

    it('approveApproval POSTs /approvals/:id/approve', async () => {
      mockPost.mockResolvedValue({ id: 1 })
      await approveApproval(1)
      expect(mockPost).toHaveBeenCalledWith('/approvals/1/approve', { approved_by: 0 })
    })

    it('rejectApproval POSTs /approvals/:id/reject', async () => {
      mockPost.mockResolvedValue({ id: 1 })
      await rejectApproval(1)
      expect(mockPost).toHaveBeenCalledWith('/approvals/1/reject', { approved_by: 0 })
    })
  })
})
