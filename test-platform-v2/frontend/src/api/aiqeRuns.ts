import client from './client'
import type {
  AiqeRun,
  AiqeRunArtifact,
  AiqeRunEvent,
  AiqeRunNodes,
  AiqeRunPage,
} from '@/types/aiqe'

interface RunDetail {
  run: AiqeRun
  events: AiqeRunEvent[]
  artifacts: AiqeRunArtifact[]
}

export async function listAiqeRuns(params: {
  limit?: number
  offset?: number
  status?: string
} = {}): Promise<AiqeRunPage> {
  return (await client.get('/aiqe/runs', { params })) as unknown as AiqeRunPage
}

export async function getAiqeRun(runId: string): Promise<RunDetail> {
  return (await client.get(`/aiqe/runs/${runId}`)) as unknown as RunDetail
}

export async function listRunEvents(
  runId: string,
  afterSeq = 0,
  limit = 500,
): Promise<{ items: AiqeRunEvent[]; last_seq: number }> {
  return (await client.get(`/aiqe/runs/${runId}/events`, {
    params: { after_seq: afterSeq, limit },
  })) as unknown as { items: AiqeRunEvent[]; last_seq: number }
}

export async function listRunArtifacts(runId: string): Promise<AiqeRunArtifact[]> {
  const data = (await client.get(`/aiqe/runs/${runId}/artifacts`)) as unknown as {
    items: AiqeRunArtifact[]
  }
  return data.items
}

export async function listRunNodes(runId: string): Promise<AiqeRunNodes> {
  return (await client.get(`/aiqe/runs/${runId}/nodes`)) as unknown as AiqeRunNodes
}
