/**
 * AITDE execution API function tests — verifies endpoint, method, and payload shape.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'

// Mock the shared AITDE v2 client BEFORE importing the module under test.
const mockGet = vi.fn()
const mockPost = vi.fn()
const mockPatch = vi.fn()

vi.mock('@/api/missions', () => ({
  aitdeV2: {
    get: (...args: any[]) => mockGet(...args),
    post: (...args: any[]) => mockPost(...args),
    patch: (...args: any[]) => mockPatch(...args),
  },
}))

// Dynamic imports after mocking.
const {
  fetchScenarioAdapters,
  createScenarioAdapter,
  updateAdapter,
  captureSnapshot,
  fetchLatestSnapshot,
  createRun,
  fetchRun,
  fetchRuns,
  fetchMissionRuns,
  cancelRun,
  retryRun,
  finishRun,
  fetchRunSteps,
  fetchRunAssertions,
  fetchRunEvidence,
  fetchRunReplay,
} = await import('@/api/executions')

describe('executions API functions', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Adapters', () => {
    it('fetchScenarioAdapters calls GET /scenarios/:id/adapters', async () => {
      mockGet.mockResolvedValue({ items: [] })
      await fetchScenarioAdapters(12)
      expect(mockGet).toHaveBeenCalledWith('/scenarios/12/adapters', expect.objectContaining({}))
    })

    it('createScenarioAdapter POSTs the payload', async () => {
      mockPost.mockResolvedValue({ id: 1 })
      const payload = {
        scenario_version_id: 3,
        adapter_type: 'PLAYWRIGHT',
        config: { headless: true },
        adapter_version: '1.0.0',
      }
      await createScenarioAdapter(12, payload)
      expect(mockPost).toHaveBeenCalledWith('/scenarios/12/adapters', payload)
    })

    it('updateAdapter PATCHes status/config', async () => {
      mockPatch.mockResolvedValue({ id: 5 })
      await updateAdapter(5, { status: 'ACTIVE' })
      expect(mockPatch).toHaveBeenCalledWith('/scenarios/adapters/5', { status: 'ACTIVE' })
    })
  })

  describe('Environment snapshot', () => {
    it('captureSnapshot POSTs /environments/:id/snapshots with mission_id param', async () => {
      mockPost.mockResolvedValue({ id: 9 })
      await captureSnapshot(3, 7, { build_label: 'build-1' })
      expect(mockPost).toHaveBeenCalledWith(
        '/environments/3/snapshots',
        { build_label: 'build-1' },
        expect.objectContaining({ params: { mission_id: 7 } }),
      )
    })

    it('fetchLatestSnapshot GETs /environments/:id/snapshots/latest', async () => {
      mockGet.mockResolvedValue(null)
      await fetchLatestSnapshot(3, 7)
      expect(mockGet).toHaveBeenCalledWith(
        '/environments/3/snapshots/latest',
        expect.objectContaining({ params: { mission_id: 7 } }),
      )
    })
  })

  describe('Runs', () => {
    it('createRun POSTs /scenarios/:id/runs with payload', async () => {
      mockPost.mockResolvedValue({ id: 42 })
      const payload = {
        mission_id: 7,
        scenario_version_id: 3,
        contract_version_id: 11,
        environment_id: 4,
        environment_snapshot_id: 9,
        adapter_id: 5,
        trigger_type: 'MANUAL',
      }
      await createRun(12, payload)
      expect(mockPost).toHaveBeenCalledWith('/scenarios/12/runs', payload)
    })

    it('fetchRun GETs /runs/:id', async () => {
      mockGet.mockResolvedValue({ id: 42 })
      await fetchRun(42)
      expect(mockGet).toHaveBeenCalledWith('/runs/42', expect.objectContaining({}))
    })

    it('fetchRuns is an alias of fetchRun', async () => {
      mockGet.mockResolvedValue({ id: 42 })
      await fetchRuns(42)
      expect(mockGet).toHaveBeenCalledWith('/runs/42', expect.objectContaining({}))
    })

    it('fetchMissionRuns GETs /missions/:id/executions with filters', async () => {
      mockGet.mockResolvedValue({ total: 1, page: 1, page_size: 20, items: [] })
      await fetchMissionRuns(7, { outcome: 'PASS', page: 2, page_size: 10 })
      expect(mockGet).toHaveBeenCalledWith(
        '/missions/7/executions',
        expect.objectContaining({
          params: { outcome: 'PASS', page: 2, page_size: 10 },
        }),
      )
    })

    it('cancelRun POSTs /runs/:id/cancel', async () => {
      mockPost.mockResolvedValue({ id: 42 })
      await cancelRun(42)
      expect(mockPost).toHaveBeenCalledWith('/runs/42/cancel')
    })

    it('retryRun POSTs /runs/:id/retry', async () => {
      mockPost.mockResolvedValue({ id: 42 })
      await retryRun(42)
      expect(mockPost).toHaveBeenCalledWith('/runs/42/retry')
    })

    it('finishRun POSTs /runs/:id/finish', async () => {
      mockPost.mockResolvedValue({ id: 42 })
      await finishRun(42)
      expect(mockPost).toHaveBeenCalledWith('/runs/42/finish')
    })
  })

  describe('Sub-resources', () => {
    it('fetchRunSteps GETs /runs/:id/steps', async () => {
      mockGet.mockResolvedValue({ items: [] })
      await fetchRunSteps(42)
      expect(mockGet).toHaveBeenCalledWith('/runs/42/steps', expect.objectContaining({}))
    })

    it('fetchRunAssertions GETs /runs/:id/assertions', async () => {
      mockGet.mockResolvedValue({ items: [] })
      await fetchRunAssertions(42)
      expect(mockGet).toHaveBeenCalledWith('/runs/42/assertions', expect.objectContaining({}))
    })

    it('fetchRunEvidence GETs /runs/:id/evidence', async () => {
      mockGet.mockResolvedValue({ items: [] })
      await fetchRunEvidence(42)
      expect(mockGet).toHaveBeenCalledWith('/runs/42/evidence', expect.objectContaining({}))
    })

    it('fetchRunReplay GETs /runs/:id/replay', async () => {
      mockGet.mockResolvedValue({ manifest: {}, hash: 'abc', view: { timeline: [] } })
      await fetchRunReplay(42)
      expect(mockGet).toHaveBeenCalledWith('/runs/42/replay', expect.objectContaining({}))
    })
  })
})
