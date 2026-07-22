import api from './client'
import type {
  ReleaseBundleOut,
  ReleaseBundleListItem,
  ReleaseBundleVersionChain,
  VersionDiffRequest,
  VersionDiffConfirmRequest,
  VersionDiffConfirmResult,
  VersionDiffResult,
  KnowledgePage,
} from '@/types'

// ── ReleaseBundle CRUD ──

export async function fetchReleaseBundles(params?: {
  status?: string
  keyword?: string
  page?: number
  page_size?: number
}): Promise<KnowledgePage<ReleaseBundleListItem>> {
  return api.get('/release-bundles', { params })
}

export async function fetchReleaseBundle(id: number): Promise<ReleaseBundleOut> {
  return api.get(`/release-bundles/${id}`)
}

export async function createReleaseBundle(body: {
  name: string
  description?: string
  client_version?: string
  admin_version?: string
  release_date?: string | null
  parent_bundle_id?: number | null
}): Promise<ReleaseBundleOut> {
  return api.post('/release-bundles', body)
}

export async function updateReleaseBundle(
  id: number,
  body: {
    name?: string
    description?: string
    client_version?: string
    admin_version?: string
    status?: string
    release_date?: string | null
    parent_bundle_id?: number | null
    diff_summary?: string
  },
): Promise<ReleaseBundleOut> {
  return api.put(`/release-bundles/${id}`, body)
}

export async function deleteReleaseBundle(id: number): Promise<void> {
  return api.delete(`/release-bundles/${id}`)
}

// ── Version Chain ──

export async function fetchVersionChain(
  id: number,
): Promise<ReleaseBundleVersionChain[]> {
  return api.get(`/release-bundles/${id}/version-chain`)
}

// ── Version Diff ──

export async function triggerVersionDiff(
  id: number,
  body: VersionDiffRequest,
): Promise<VersionDiffResult> {
  return api.post(`/release-bundles/${id}/diff`, body)
}

export async function confirmVersionDiff(
  id: number,
  body?: VersionDiffConfirmRequest,
): Promise<VersionDiffConfirmResult> {
  return api.post(`/release-bundles/${id}/diff/confirm`, body || {})
}
