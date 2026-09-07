// AI Debug Drawer tests (v331-remediation-2 B2 / V30-085)
import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { TooltipProvider } from '@/components/ui/tooltip'

import { AiDebugDrawer, parseTokenUsage } from '../AiDebugDrawer'
import { useAuthStore } from '@/stores/auth'

function makeOp(overrides: Record<string, unknown> = {}) {
  return {
    id: 7,
    project_id: 1,
    mission_id: 1,
    operation_type: 'scope:analyze',
    status: 'SUCCEEDED',
    model_provider: 'internal',
    model_name: 'deterministic-v1',
    prompt_version: 'scope_analysis_v1:abc123',
    schema_version: '1.0',
    result_ref_json: '{"secret":"should-not-render"}',
    error_code: '',
    error_message: 'stack trace with credentials',
    duration_ms: 1234,
    token_usage_json: '{"input_tokens":120,"output_tokens":30,"total_tokens":150,"cached_input_tokens":80,"uncached_input_tokens":40,"cache_hit_rate":0.6667,"cache_details_available":true,"deduplicated_request_count":1}',
    created_at: '2026-08-29T00:00:00',
    finished_at: '2026-08-29T00:00:01',
    ...overrides,
  }
}

function renderDrawer(permission: string[]) {
  useAuthStore.setState({ permissions: permission })
  return render(
    <TooltipProvider>
      <AiDebugDrawer missionId={1} open onOpenChange={() => {}} />
    </TooltipProvider>,
  )
}

// mock 抽屉的请求：直接预置 store 数据（拦截器在 jsdom 下无后端）
vi.mock('@/api/aiOperations', async (importOriginal) => {
  const mod = await importOriginal<typeof import('@/api/aiOperations')>()
  return {
    ...mod,
    fetchAiOperations: vi.fn(() =>
      Promise.resolve([
        makeOp(),
      ]),
    ),
  }
})

describe('AiDebugDrawer（V30-085）', () => {
  it('有 mission:ai_view_debug 权限时展示五要素（model/prompt/status/duration/token）', async () => {
    renderDrawer(['mission:ai_view_debug'])
    expect(await screen.findByText('scope:analyze')).toBeTruthy()
    expect(screen.getByText('internal/deterministic-v1')).toBeTruthy()
    expect(screen.getByText('scope_analysis_v1:abc123')).toBeTruthy()
    expect(screen.getByText('1234 ms')).toBeTruthy()
    expect(screen.getByText('120')).toBeTruthy()
    expect(screen.getByText('80')).toBeTruthy()
    expect(screen.getByText('40')).toBeTruthy()
    expect(screen.getByText('30')).toBeTruthy()
    expect(screen.getByText('66.67%')).toBeTruthy()
    expect(screen.getByText('1 次')).toBeTruthy()
  })

  it('无权限时不渲染任何调试内容', () => {
    renderDrawer(['mission:list'])
    expect(screen.queryByText('AI 调试信息')).toBeNull()
    expect(screen.queryByText('scope:analyze')).toBeNull()
  })

  it('不展示 error_message / result_ref 等内部细节（无 secret / CoT 泄漏面）', async () => {
    renderDrawer(['*'])
    await screen.findByText('scope:analyze')
    expect(screen.queryByText(/stack trace with credentials/)).toBeNull()
    expect(screen.queryByText(/should-not-render/)).toBeNull()
  })

  it('parseTokenUsage 区分零命中与供应商未提供缓存明细', () => {
    expect(parseTokenUsage('{"input_tokens":10,"output_tokens":2,"cached_input_tokens":0,"uncached_input_tokens":10,"cache_hit_rate":0,"cache_details_available":true}')).toEqual({
      inputTokens: 10,
      outputTokens: 2,
      cachedInputTokens: 0,
      uncachedInputTokens: 10,
      cacheHitRate: 0,
      cacheDetailsAvailable: true,
      deduplicatedRequests: 0,
    })
    expect(parseTokenUsage('{"input_tokens":10,"output_tokens":2}')).toEqual({
      inputTokens: 10,
      outputTokens: 2,
      cachedInputTokens: null,
      uncachedInputTokens: null,
      cacheHitRate: null,
      cacheDetailsAvailable: false,
      deduplicatedRequests: 0,
    })
    expect(parseTokenUsage('not-json')).toBeNull()
    expect(parseTokenUsage('{}')).toBeNull()
  })
})
