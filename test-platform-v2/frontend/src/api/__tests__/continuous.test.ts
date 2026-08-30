/**
 * AITDE V3.5 Continuous Acceptance API function tests — endpoint, method, payload.
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
  captureFingerprint,
  fetchMissionBuilds,
  createCampaign,
  fetchCampaign,
  fetchMissionCampaigns,
  runCampaign,
  fetchMissionAcceptance,
  evaluateGate,
  fetchRunProfiles,
  fetchTriggers,
} = await import('@/api/continuous')

describe('continuous API functions', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('captureFingerprint POSTs /environments/:id/fingerprints/capture', async () => {
    mockPost.mockResolvedValue({ id: 1 })
    await captureFingerprint(2, { build_label: 'b1' })
    expect(mockPost).toHaveBeenCalledWith('/environments/2/fingerprints/capture', { build_label: 'b1' })
  })

  it('fetchMissionBuilds GETs /missions/:id/builds', async () => {
    mockGet.mockResolvedValue({ items: [] })
    await fetchMissionBuilds(7)
    expect(mockGet).toHaveBeenCalledWith('/missions/7/builds', expect.objectContaining({}))
  })

  it('createCampaign POSTs /campaigns', async () => {
    mockPost.mockResolvedValue({ id: 1 })
    const payload = { project_id: 1, mission_id: 7, environment_id: 2, campaign_type: 'FULL' }
    await createCampaign(payload)
    expect(mockPost).toHaveBeenCalledWith('/campaigns', payload)
  })

  it('fetchCampaign GETs /campaigns/:id', async () => {
    mockGet.mockResolvedValue({ id: 1 })
    await fetchCampaign(1)
    expect(mockGet).toHaveBeenCalledWith('/campaigns/1', expect.objectContaining({}))
  })

  it('fetchMissionCampaigns GETs /missions/:id/campaigns', async () => {
    mockGet.mockResolvedValue({ items: [] })
    await fetchMissionCampaigns(7)
    expect(mockGet).toHaveBeenCalledWith('/missions/7/campaigns', expect.objectContaining({}))
  })

  it('runCampaign POSTs /campaigns/:id/run', async () => {
    mockPost.mockResolvedValue({ id: 1 })
    await runCampaign(1)
    expect(mockPost).toHaveBeenCalledWith('/campaigns/1/run')
  })

  it('fetchMissionAcceptance GETs /missions/:id/acceptance', async () => {
    mockGet.mockResolvedValue({ items: [] })
    await fetchMissionAcceptance(7)
    expect(mockGet).toHaveBeenCalledWith('/missions/7/acceptance', expect.objectContaining({}))
  })

  it('evaluateGate POSTs /missions/:id/quality-gates/evaluate', async () => {
    mockPost.mockResolvedValue({ id: 1 })
    await evaluateGate(7, { campaign_id: 3 })
    expect(mockPost).toHaveBeenCalledWith('/missions/7/quality-gates/evaluate', { campaign_id: 3 })
  })

  it('fetchRunProfiles GETs /run-profiles', async () => {
    mockGet.mockResolvedValue({ items: [] })
    await fetchRunProfiles()
    expect(mockGet).toHaveBeenCalledWith('/run-profiles', expect.objectContaining({}))
  })

  it('fetchTriggers GETs /triggers', async () => {
    mockGet.mockResolvedValue({ items: [] })
    await fetchTriggers()
    expect(mockGet).toHaveBeenCalledWith('/triggers', expect.objectContaining({}))
  })
})
