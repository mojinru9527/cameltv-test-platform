import { describe, expect, it } from 'vitest'

import { buildIntegrationAuthJson } from './authPayload'

describe('buildIntegrationAuthJson', () => {
  it('omits auth_json when an edit leaves all credential fields blank', () => {
    expect(buildIntegrationAuthJson({
      provider_type: 'jira',
      email: '',
      api_token: '',
      project_key: '',
    }, true)).toBeUndefined()
  })

  it('sends only explicitly entered Jira fields during an edit', () => {
    expect(JSON.parse(buildIntegrationAuthJson({
      provider_type: 'jira',
      email: '',
      api_token: '',
      project_key: 'CAMEL',
    }, true) ?? '{}')).toEqual({ project_key: 'CAMEL' })
  })

  it('keeps create payloads explicit even when credentials are unavailable', () => {
    expect(buildIntegrationAuthJson({
      provider_type: 'tapd',
      api_user: '',
      api_password: '',
      workspace_id: '',
    }, false)).toBe('{}')
  })
})
