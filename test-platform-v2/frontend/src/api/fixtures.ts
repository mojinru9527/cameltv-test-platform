import { aitdeV2 } from './missions'

// ── AITDE V3.2 Data + DB Runtime: Fixture domain ──

export interface FixtureEntity {
  entity_id: string
  entity_type: string
  snapshot_type?: string | null
  storage_uri?: string | null
  row_count?: number | null
  content_hash?: string | null
}

export interface Fixture {
  id: number
  project_id: number
  scenario_version_id: number
  run_id: number | null
  data_plan_id: number | null
  environment_id: number | null
  data_source_id: number | null
  strategy: string | null
  status: string
  namespace: string | null
  manifest_json: Record<string, unknown> | null
  created_at: string | null
  expires_at: string | null
  cleanup_status: string | null
  entities: FixtureEntity[]
}

export interface FixtureLease {
  id: number
  fixture_id: number
  run_id: number
  status: string
}

export interface ReleaseFixtureResult {
  id: number
  status: string
}

export interface FixtureCleanupResult {
  status: string
  attempt_no: number
  actions: Record<string, unknown> | null
  idempotent: boolean
}

export interface FixtureSnapshot {
  id: number
  fixture_id: number
  run_id: number | null
  entity_id: string | null
  snapshot_type: string
  storage_uri: string | null
  snapshot_json: Record<string, unknown> | null
  content_hash: string | null
  created_at: string | null
}

export interface LeaseFixtureInput {
  run_id: number
  ttl_seconds?: number
}

export function fetchFixture(fixtureId: number, signal?: AbortSignal): Promise<Fixture> {
  return aitdeV2.get(`/fixtures/${fixtureId}`, { signal })
}

export function leaseFixture(fixtureId: number, payload: LeaseFixtureInput): Promise<FixtureLease> {
  return aitdeV2.post(`/fixtures/${fixtureId}/lease`, payload)
}

export function releaseFixture(
  fixtureId: number,
  payload: { lease_id: number },
): Promise<ReleaseFixtureResult> {
  return aitdeV2.post(`/fixtures/${fixtureId}/release`, payload)
}

export function cleanupFixture(fixtureId: number): Promise<FixtureCleanupResult> {
  return aitdeV2.post(`/fixtures/${fixtureId}/cleanup`)
}

export function fetchFixtureSnapshots(
  fixtureId: number,
  signal?: AbortSignal,
): Promise<FixtureSnapshot[]> {
  return aitdeV2.get(`/fixtures/${fixtureId}/snapshots`, { signal })
}

// ── UI label/colour maps ──

export const FIXTURE_STATUS_LABELS: Record<string, { label: string; color: string }> = {
  PROVISIONING: { label: '预置中', color: 'bg-status-info-muted text-status-info' },
  READY: { label: '就绪', color: 'bg-status-success-muted text-status-success' },
  LEASED: { label: '已租用', color: 'bg-status-warning-muted text-status-warning' },
  EXPIRED: { label: '已过期', color: 'bg-muted text-muted-foreground' },
  CLEANING: { label: '清理中', color: 'bg-status-info-muted text-status-info' },
  CLEANED: { label: '已清理', color: 'bg-status-success-muted text-status-success' },
  CLEANUP_FAILED: { label: '清理失败', color: 'bg-status-danger-muted text-status-danger' },
  RELEASED: { label: '已释放', color: 'bg-status-info-muted text-status-info' },
}
