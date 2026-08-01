import { describe, expect, it } from 'vitest'

import { buildApiExecutionRequest } from '../apiExecutionRequest'

describe('ApiExecutionRequest builder', () => {
  it.each(['quick', 'asset', 'single', 'group', 'batch'] as const)(
    'normalizes the %s entry point with one shared contract',
    (source) => {
      const request = buildApiExecutionRequest({
        source,
        environmentId: 7,
        datasetId: 11,
        caseIds: source === 'quick' || source === 'asset' ? [] : source === 'single' ? [21] : [21, 22],
        request: source === 'quick' || source === 'asset'
          ? {
              method: 'GET',
              url: '/items',
              headers: '{"X-Trace":"${TRACE_ID}"}',
              body: '',
              queryParams: '{"page":"${PAGE}","limit":20}',
              assertions: '[{"type":"status_code","operator":"eq","expected":200}]',
            }
          : null,
        confirmProd: false,
      })

      expect(request.source).toBe(source)
      expect(request.environment_id).toBe(7)
      expect(request.dataset_id).toBe(11)
      expect(request.case_ids).toEqual(
        source === 'quick' || source === 'asset' ? [] : source === 'single' ? [21] : [21, 22],
      )
      if (request.request) {
        expect(request.request.query_params).toEqual({ page: '${PAGE}', limit: 20 })
        expect(request.request.assertions[0].expected).toBe(200)
        expect(typeof request.request.assertions[0].expected).toBe('number')
      }
    },
  )

  it('uses explicit nulls instead of silently dropping environment and dataset selection', () => {
    const request = buildApiExecutionRequest({
      source: 'single',
      caseIds: [8],
      request: null,
    })

    expect(request).toMatchObject({
      environment_id: null,
      dataset_id: null,
      confirm_prod: false,
    })
  })

  it('rejects quick execution without a request definition', () => {
    expect(() => buildApiExecutionRequest({ source: 'quick', request: null })).toThrow(
      'quick execution requires a request definition',
    )
  })
})
