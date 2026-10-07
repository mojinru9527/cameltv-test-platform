/**
 * Knowledge API function tests — verifies correct endpoint, method, and payload shape.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'

// Mock the axios client BEFORE importing the module under test
const mockGet = vi.fn()
const mockPost = vi.fn()

vi.mock('@/api/client', () => ({
  default: {
    get: (...args: any[]) => mockGet(...args),
    post: (...args: any[]) => mockPost(...args),
  },
}))

// Dynamic imports after mocking
const {
  fetchKnowledgeOverview,
  fetchKnowledgeSources,
  fetchKnowledgeSource,
  fetchSourceChunks,
  searchKnowledge,
  reembedKnowledge,
} = await import('@/api/knowledge')

describe('Knowledge API functions', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('fetchKnowledgeOverview', () => {
    it('calls GET /knowledge/overview', async () => {
      mockGet.mockResolvedValue({ source_count: 5, chunk_count: 10 })
      const result = await fetchKnowledgeOverview()
      expect(mockGet).toHaveBeenCalledWith('/knowledge/overview')
      expect(result).toEqual({ source_count: 5, chunk_count: 10 })
    })
  })

  describe('fetchKnowledgeSources', () => {
    it('calls GET /knowledge/sources with params', async () => {
      mockGet.mockResolvedValue({ total: 3, items: [], page: 1, page_size: 20 })
      await fetchKnowledgeSources({ source_type: 'test_case', page: 1, page_size: 10 })
      expect(mockGet).toHaveBeenCalledWith('/knowledge/sources', {
        params: { source_type: 'test_case', page: 1, page_size: 10 },
      })
    })

    it('calls GET /knowledge/sources without optional params', async () => {
      mockGet.mockResolvedValue({ total: 0, items: [], page: 1, page_size: 20 })
      await fetchKnowledgeSources({})
      expect(mockGet).toHaveBeenCalledWith('/knowledge/sources', { params: {} })
    })
  })

  describe('fetchKnowledgeSource', () => {
    it('calls GET /knowledge/sources/:id', async () => {
      mockGet.mockResolvedValue({ id: 42, title: 'Test Source' })
      const result = await fetchKnowledgeSource(42)
      expect(mockGet).toHaveBeenCalledWith('/knowledge/sources/42')
      expect(result).toEqual({ id: 42, title: 'Test Source' })
    })
  })

  describe('fetchSourceChunks', () => {
    it('calls GET /knowledge/sources/:id/chunks', async () => {
      mockGet.mockResolvedValue([{ id: 1, content: 'chunk content' }])
      await fetchSourceChunks(7)
      expect(mockGet).toHaveBeenCalledWith('/knowledge/sources/7/chunks')
    })
  })

  describe('searchKnowledge', () => {
    it('calls POST /knowledge/search with query body', async () => {
      mockPost.mockResolvedValue([{ chunk_id: 1, snippet: 'match', score: 0.95 }])
      const result = await searchKnowledge({ query: '密码校验', top_k: 5, mode: 'hybrid' })
      expect(mockPost).toHaveBeenCalledWith('/knowledge/search', {
        query: '密码校验', top_k: 5, mode: 'hybrid',
      })
      expect(result).toHaveLength(1)
    })

    it('defaults mode and chunk_type when omitted', async () => {
      mockPost.mockResolvedValue([])
      await searchKnowledge({ query: 'test' })
      expect(mockPost).toHaveBeenCalledWith('/knowledge/search', { query: 'test' })
    })
  })

  describe('reembedKnowledge', () => {
    it('calls POST /knowledge/reembed', async () => {
      mockPost.mockResolvedValue({ total: 10, embedded: 8, skipped: 2 })
      const result = await reembedKnowledge()
      expect(mockPost).toHaveBeenCalledWith('/knowledge/reembed')
      expect(result.embedded).toBe(8)
    })
  })
})
