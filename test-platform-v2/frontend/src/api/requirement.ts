import api from './client'
import type {
  AIGenerateResult,
  FeatureExtractionResult,
  ExtractionConfirmRequest,
  RequirementDocument,
} from '@/types'

export async function fetchRequirements(): Promise<RequirementDocument[]> {
  return api.get('/requirements')
}

export async function uploadRequirement(data: FormData): Promise<RequirementDocument> {
  return api.post('/requirements/upload', data)
}

export async function extractFeatures(documentId: number): Promise<FeatureExtractionResult> {
  return api.post(`/requirements/${documentId}/extract`)
}

export async function getExtraction(documentId: number): Promise<FeatureExtractionResult> {
  return api.get(`/requirements/${documentId}/extraction`)
}

export async function confirmExtraction(
  documentId: number,
  data: ExtractionConfirmRequest
): Promise<Record<string, unknown>> {
  return api.post(`/requirements/${documentId}/extraction/confirm`, data)
}

export async function generateTestCases(
  documentId: number,
  options?: { use_extraction?: boolean }
): Promise<AIGenerateResult> {
  return api.post(`/requirements/${documentId}/generate`, options || {})
}

export async function importCases(
  documentId: number,
  indices: number[]
): Promise<{ imported: number; skipped: number; total: number }> {
  return api.post(`/requirements/${documentId}/import`, { indices })
}

export async function fetchGeneratedCases(documentId: number): Promise<AIGenerateResult> {
  return api.get(`/requirements/${documentId}/cases`)
}

export async function deleteRequirement(documentId: number): Promise<void> {
  return api.delete(`/requirements/${documentId}`)
}
