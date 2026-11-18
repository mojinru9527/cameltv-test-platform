import client from './client'

export interface AiqeArtifactDetail {
  id: string
  run_id: string
  node_run_id: string | null
  artifact_type: string
  content_type: string
  sha256: string
  size_bytes: number
  upload_status: string
  redaction_status: string
  retention_until: string | null
  deleted_at: string | null
  created_at: string
  metadata: Record<string, unknown>
}

export interface AiqeArtifactSession {
  artifact: AiqeArtifactDetail
  upload: {
    artifact_id: string
    upload_url: string
    method: string
    content_type: string
    expires_at: string
    max_bytes: number
  }
}

export async function createArtifactSession(payload: {
  run_id: string
  artifact_type: string
  content_type?: string
  node_run_id?: string | null
  expected_sha256?: string
  expected_size_bytes?: number
  retention_days?: number
}): Promise<AiqeArtifactSession> {
  return (await client.post('/aiqe/artifacts', payload)) as unknown as AiqeArtifactSession
}

export async function uploadArtifactContent(artifactId: string, content: Blob): Promise<AiqeArtifactDetail> {
  const data = (await client.put(`/aiqe/artifacts/${artifactId}/content`, content, {
    headers: { 'Content-Type': content.type || 'application/octet-stream' },
  })) as unknown as { artifact: AiqeArtifactDetail }
  return data.artifact
}

export async function getArtifact(artifactId: string): Promise<AiqeArtifactDetail> {
  return (await client.get(`/aiqe/artifacts/${artifactId}`)) as unknown as AiqeArtifactDetail
}

/**
 * 下载（查看）Artifact：先经后端重新鉴权，再取 blob 生成短期 object URL。
 * 禁止把永久公开 URL 直接放进页面（AUD-008 §7）。
 */
export async function fetchArtifactBlob(artifactId: string): Promise<Blob> {
  return (await client.get(`/aiqe/artifacts/${artifactId}/content`, {
    responseType: 'blob',
    suppressErrorToast: true,
  } as never)) as unknown as Blob
}
