/**
 * AITDE V3.6 Production Evidence API function tests — endpoint, method, payload.
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
  startObservationSession,
  stopObservationSession,
  fetchObservationSession,
  fetchJourneys,
  fetchJourney,
  inspectProductionData,
  extractEntityGraph,
  buildTemplate,
  validateTemplate,
  materializeTemplate,
  analyzeGaps,
} = await import('@/api/production')

describe('production API functions', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('startObservationSession POSTs /production/observation-sessions', async () => {
    mockPost.mockResolvedValue({ id: 1 })
    await startObservationSession({ project_id: 1, environment_id: 2, mode: 'OBSERVE' })
    expect(mockPost).toHaveBeenCalledWith('/production/observation-sessions', {
      project_id: 1,
      environment_id: 2,
      mode: 'OBSERVE',
    })
  })

  it('stopObservationSession POSTs /production/observation-sessions/:id/stop', async () => {
    mockPost.mockResolvedValue({ id: 5 })
    await stopObservationSession(5)
    expect(mockPost).toHaveBeenCalledWith('/production/observation-sessions/5/stop')
  })

  it('fetchObservationSession GETs /production/observation-sessions/:id', async () => {
    mockGet.mockResolvedValue({ id: 1 })
    await fetchObservationSession(1)
    expect(mockGet).toHaveBeenCalledWith('/production/observation-sessions/1', expect.objectContaining({}))
  })

  it('fetchJourneys GETs /production/journeys with session_id param', async () => {
    mockGet.mockResolvedValue([])
    await fetchJourneys(7)
    expect(mockGet).toHaveBeenCalledWith('/production/journeys', expect.objectContaining({ params: { session_id: 7 } }))
  })

  it('fetchJourneys GETs /production/journeys without params when no session', async () => {
    mockGet.mockResolvedValue([])
    await fetchJourneys()
    expect(mockGet).toHaveBeenCalledWith('/production/journeys', expect.objectContaining({ params: undefined }))
  })

  it('fetchJourney GETs /production/journeys/:id', async () => {
    mockGet.mockResolvedValue({ id: 1, steps: [] })
    await fetchJourney(1)
    expect(mockGet).toHaveBeenCalledWith('/production/journeys/1', expect.objectContaining({}))
  })

  it('inspectProductionData POSTs /production/data/inspect', async () => {
    mockPost.mockResolvedValue({ rows: [], row_count: 0, duration_ms: 1 })
    await inspectProductionData({ project_id: 1, data_source_id: 2, sql: 'SELECT 1' })
    expect(mockPost).toHaveBeenCalledWith('/production/data/inspect', {
      project_id: 1,
      data_source_id: 2,
      sql: 'SELECT 1',
    })
  })

  it('extractEntityGraph POSTs /production/entity-graphs/extract', async () => {
    mockPost.mockResolvedValue({ id: 1, content_hash: 'abc', nodes: [], edges: [] })
    await extractEntityGraph({ project_id: 1, root_entity_type: 'User', root_ref_hash: 'h', source_environment_id: 2 })
    expect(mockPost).toHaveBeenCalledWith('/production/entity-graphs/extract', {
      project_id: 1,
      root_entity_type: 'User',
      root_ref_hash: 'h',
      source_environment_id: 2,
    })
  })

  it('buildTemplate POSTs /production/templates', async () => {
    mockPost.mockResolvedValue({ id: 1, validation_status: 'DRAFT' })
    await buildTemplate({ project_id: 1, name: 't', entity_graph_snapshot_id: 3 })
    expect(mockPost).toHaveBeenCalledWith('/production/templates', {
      project_id: 1,
      name: 't',
      entity_graph_snapshot_id: 3,
    })
  })

  it('validateTemplate POSTs /production/templates/:id/validate', async () => {
    mockPost.mockResolvedValue({ validation_status: 'VALID', leaks: [] })
    await validateTemplate(4, { project_id: 1, template_id: 4 })
    expect(mockPost).toHaveBeenCalledWith('/production/templates/4/validate', {
      project_id: 1,
      template_id: 4,
    })
  })

  it('materializeTemplate POSTs /production/templates/:id/materialize', async () => {
    mockPost.mockResolvedValue({ materialization_id: 9 })
    await materializeTemplate(4, { project_id: 1, template_id: 4, target_environment_id: 2 })
    expect(mockPost).toHaveBeenCalledWith('/production/templates/4/materialize', {
      project_id: 1,
      template_id: 4,
      target_environment_id: 2,
    })
  })

  it('analyzeGaps POSTs /production/evidence/:journey_id/analyze-gaps', async () => {
    mockPost.mockResolvedValue([])
    await analyzeGaps(6, { project_id: 1, journey_id: 6 })
    expect(mockPost).toHaveBeenCalledWith('/production/evidence/6/analyze-gaps', {
      project_id: 1,
      journey_id: 6,
    })
  })
})
