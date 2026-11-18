import client from './client'

export interface ImpactCandidate {
  case_id: string
  score: number
  reason: string
  trace_path: string
}

export interface ImpactPlan {
  base_sha: string
  head_sha: string
  changed_files: Array<{ path: string; status: string; added: number; removed: number }>
  components: string[]
  changed_symbols: Record<string, string[]>
  changed_routes: string[]
  changed_migrations: string[]
  mandatory_case_ids: string[]
  candidates: ImpactCandidate[]
}

export interface BenchmarkDataset {
  id: string
  dataset_key: string
  revision: number
}

export interface BenchmarkRunView {
  id: string
  dataset_id: string
  agent_key: string
  status: string
  result_status: string
  metrics: Record<string, unknown> | null
  per_sample: Array<Record<string, unknown>> | null
}

export async function createImpactPlan(payload: {
  base_sha: string
  head_sha: string
  failed_case_ids?: string[]
  changed_contract_ids?: string[]
  ai_proposed_case_ids?: string[]
}): Promise<ImpactPlan> {
  return (await client.post('/aiqe/impact/plan', payload)) as unknown as ImpactPlan
}

export async function createBenchmarkDataset(payload: {
  dataset_key: string
  task_type: string
}): Promise<BenchmarkDataset> {
  return (await client.post('/aiqe/benchmarks/datasets', payload)) as unknown as BenchmarkDataset
}

export async function addBenchmarkSample(
  datasetId: string,
  payload: { sample_id: string; golden_labels: string[]; labeler?: string; reviewer?: string },
): Promise<{ id: string; sample_id: string }> {
  return (await client.post(`/aiqe/benchmarks/datasets/${datasetId}/samples`, payload)) as unknown as {
    id: string
    sample_id: string
  }
}

export async function freezeBenchmarkDataset(datasetId: string): Promise<{
  id: string
  status: string
  sample_count: number
  content_hash: string
  gate_eligible: boolean
}> {
  return (await client.post(`/aiqe/benchmarks/datasets/${datasetId}/freeze`)) as unknown as {
    id: string
    status: string
    sample_count: number
    content_hash: string
    gate_eligible: boolean
  }
}

export async function getBenchmarkRun(runId: string): Promise<BenchmarkRunView> {
  return (await client.get(`/aiqe/benchmarks/runs/${runId}`)) as unknown as BenchmarkRunView
}
