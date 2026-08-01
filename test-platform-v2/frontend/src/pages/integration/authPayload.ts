export interface IntegrationAuthFields {
  provider_type: 'jira' | 'tapd'
  email?: string
  api_token?: string
  api_user?: string
  api_password?: string
  project_key?: string
  workspace_id?: string
}

function includeNonBlank(target: Record<string, string>, key: string, value?: string) {
  if (value?.trim()) target[key] = value
}

export function buildIntegrationAuthJson(
  values: IntegrationAuthFields,
  preserveWhenBlank: boolean,
): string | undefined {
  const auth: Record<string, string> = {}

  if (values.provider_type === 'jira') {
    includeNonBlank(auth, 'email', values.email)
    includeNonBlank(auth, 'api_token', values.api_token)
    includeNonBlank(auth, 'project_key', values.project_key)
  } else {
    includeNonBlank(auth, 'api_user', values.api_user)
    includeNonBlank(auth, 'api_password', values.api_password)
    includeNonBlank(auth, 'workspace_id', values.workspace_id)
  }

  if (preserveWhenBlank && Object.keys(auth).length === 0) return undefined
  return JSON.stringify(auth)
}
