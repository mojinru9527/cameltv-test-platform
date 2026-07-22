import api from './client'
import type {
  RequirementModuleOut,
  RequirementModuleBrief,
  ModuleTreeNode,
  ModuleTreeResponse,
  ModuleTestSummaryOut,
  ModuleAdminLinkOut,
  GlobalNavItemOut,
  TestLinkingResult,
  AttachmentExtractResultOut,
  KnowledgePage,
} from '@/types'

// ── Module Queries ──

export async function fetchModules(params?: {
  release_bundle_id?: number
  node_type?: string
  platform?: string
  change_type?: string
  keyword?: string
  page?: number
  page_size?: number
}): Promise<KnowledgePage<RequirementModuleBrief>> {
  return api.get('/requirement-modules', { params })
}

export async function fetchModule(id: number): Promise<RequirementModuleOut> {
  return api.get(`/requirement-modules/${id}`)
}

// ── Module Tree ──

export async function fetchModuleTree(
  bundleId: number,
): Promise<ModuleTreeResponse> {
  return api.get(`/requirement-modules/bundle/${bundleId}/tree`)
}

export async function fetchModuleChildren(
  bundleId: number,
  parentId: number,
): Promise<ModuleTreeNode[]> {
  return api.get(`/requirement-modules/bundle/${bundleId}/children/${parentId}`)
}

// ── Module Extraction ──

export async function extractModules(body: {
  evidence_job_id: number
  document_id?: number | null
  source_version?: string
}): Promise<{
  module_ids: number[]
  module_count: number
  page_count: number
  attachment_count: number
  changelog_entries: number
  warnings: string[]
}> {
  return api.post('/requirement-modules/bundle/extract', body)
}

// ── Test Case Linking ──

export async function linkTestCases(
  bundleId: number,
): Promise<TestLinkingResult> {
  return api.post(`/requirement-modules/bundle/${bundleId}/link-test-cases`)
}

export async function fetchModuleTestSummary(
  moduleId: number,
): Promise<ModuleTestSummaryOut> {
  return api.get(`/requirement-modules/${moduleId}/test-summary`)
}

// ── Interactions ──

export async function extractInteractions(
  bundleId: number,
  body?: { preferred_layers?: string[] },
): Promise<{ extracted: number; pages_processed: number }> {
  return api.post(
    `/requirement-modules/bundle/${bundleId}/extract-interactions`,
    body || {},
  )
}

export async function saveInteractions(
  moduleId: number,
  body: { interactions: Record<string, unknown>[]; merge?: boolean },
): Promise<{ saved: number }> {
  return api.put(`/requirement-modules/${moduleId}/interactions`, body)
}

// ── Global Navigation ──

export async function classifyGlobalNav(
  bundleId: number,
  body?: { threshold?: number },
): Promise<{ total_items: number }> {
  return api.post(
    `/requirement-modules/bundle/${bundleId}/classify-global-nav`,
    body || {},
  )
}

export async function fetchGlobalNav(
  bundleId: number,
): Promise<GlobalNavItemOut[]> {
  return api.get(`/requirement-modules/bundle/${bundleId}/global-nav`)
}

// ── Configures (Admin Links) ──

export async function suggestConfigures(
  bundleId: number,
  body?: { client_version?: string; admin_version?: string },
): Promise<{ suggestions: Record<string, unknown>[] }> {
  return api.post(
    `/requirement-modules/bundle/${bundleId}/suggest-configures`,
    body || {},
  )
}

export async function confirmConfigures(
  bundleId: number,
  body?: { suggestion_indices?: number[]; min_confidence?: number },
): Promise<{ confirmed: number; skipped: number }> {
  return api.post(
    `/requirement-modules/bundle/${bundleId}/confirm-configures`,
    body || {},
  )
}

export async function fetchAdminLinks(
  bundleId: number,
): Promise<ModuleAdminLinkOut[]> {
  return api.get(`/requirement-modules/bundle/${bundleId}/admin-links`)
}

export async function createAdminLink(body: {
  client_module_id: number
  admin_module_id: number
  relation_type?: string
}): Promise<ModuleAdminLinkOut> {
  return api.post('/requirement-modules/admin-links', body)
}

export async function deleteAdminLink(id: number): Promise<void> {
  return api.delete(`/requirement-modules/admin-links/${id}`)
}

// ── Attachments ──

export async function extractAttachments(
  bundleId: number,
  body?: { version?: string },
): Promise<AttachmentExtractResultOut> {
  return api.post(
    `/requirement-modules/bundle/${bundleId}/extract-attachments`,
    body || {},
  )
}
