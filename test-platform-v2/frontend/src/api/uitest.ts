import api from './client'
import type { UiJobItem, UiRunItem, UiRunArtifact, RunnerHealth } from '@/types'

export async function fetchUiJobs(params: Record<string, any> = {}) {
  return api.get('/ui-tests', { params })
}

export async function fetchUiJob(id: number) {
  return api.get(`/ui-tests/${id}`)
}

export async function createUiJob(body: Record<string, any>) {
  return api.post('/ui-tests', body)
}

export async function updateUiJob(id: number, body: Record<string, any>) {
  return api.put(`/ui-tests/${id}`, body)
}

export async function deleteUiJob(id: number) {
  return api.delete(`/ui-tests/${id}`)
}

export async function triggerUiJob(id: number) {
  return api.post(`/ui-tests/${id}/trigger`)
}

export async function fetchUiRuns(jobId: number, params: Record<string, any> = {}) {
  return api.get(`/ui-tests/${jobId}/runs`, { params })
}

export async function fetchRunDetail(runId: number): Promise<UiRunItem> {
  return api.get(`/ui-tests/runs/${runId}`)
}

export async function cancelRun(runId: number): Promise<{ status: string; run_id: number }> {
  return api.post(`/ui-tests/runs/${runId}/cancel`)
}

export async function fetchRunArtifacts(runId: number): Promise<UiRunArtifact[]> {
  return api.get(`/ui-tests/runs/${runId}/artifacts`)
}

export async function fetchRunnerHealth(): Promise<RunnerHealth> {
  return api.get('/ui-tests/runner/health')
}

export async function fetchScripts(): Promise<string[]> {
  const res: any = await api.get('/ui-tests/scripts')
  return res?.available_specs ?? []
}
