import { aitdeV2 } from './missions'
import { parseJson } from './json'

// ── AITDE V3.2 Data + DB Runtime: Fixture domain ──

export interface FixtureEntity {
  id: number
  fixture_id: number
  entity_type: string
  logical_key: string
  /** Backend sends a JSON string; parsed to an object here. */
  physical_ref_json: Record<string, unknown> | null
  created_by_fixture: boolean
  cleanup_action_json: Record<string, unknown> | null
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
  /** Backend emits a JSON string (array of entity specs or an object); parsed to a value here. */
  manifest_json: unknown
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
  entity_id: number | null
  snapshot_type: string
  storage_uri: string | null
  /** Backend sends a JSON string; parsed to an object here. */
  snapshot_json: Record<string, unknown> | null
  content_hash: string | null
  created_at: string | null
}

export interface LeaseFixtureInput {
  run_id: number
  ttl_seconds?: number
}

interface RawFixtureEntity extends Omit<FixtureEntity, 'physical_ref_json' | 'cleanup_action_json'> {
  physical_ref_json?: string | null
  cleanup_action_json?: string | null
}

interface RawFixture extends Omit<Fixture, 'manifest_json' | 'entities'> {
  manifest_json?: string | null
  entities?: RawFixtureEntity[]
}interface RawSnapshot extends Omit<FixtureSnapshot, 'snapshot_json'> {
  snapshot_json?: string | null
}

function mapEntity(raw: RawFixtureEntity): FixtureEntity {
  return {
    ...raw,
    physical_ref_json: parseJson(raw.physical_ref_json),
    cleanup_action_json: parseJson(raw.cleanup_action_json),
  }
}

function mapFixture(raw: RawFixture): Fixture {
  return {
    ...raw,
    manifest_json: parseJson<unknown>(raw.manifest_json),
    entities: (raw.entities ?? []).map(mapEntity),
  }
}

function mapSnapshot(raw: RawSnapshot): FixtureSnapshot {
  return {
    ...raw,
    snapshot_json: parseJson(raw.snapshot_json),
  }
}

export async function fetchFixture(fixtureId: number, signal?: AbortSignal): Promise<Fixture> {
  const raw = (await aitdeV2.get(`/fixtures/${fixtureId}`, { signal })) as RawFixture
  return mapFixture(raw)
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

export async function fetchFixtureSnapshots(
  fixtureId: number,
  signal?: AbortSignal,
): Promise<FixtureSnapshot[]> {
  const rows = (await aitdeV2.get(`/fixtures/${fixtureId}/snapshots`, { signal })) as RawSnapshot[]
  return (rows ?? []).map(mapSnapshot)
}

// ── UI label/colour maps ──
export const FIXTURE_STATUS_LABELS: Record<string, { label: string; color: string }> = {
  PROVISIONING: { label: '预置中', color: 'bg-status-info-muted text-status-info' },
  READY: { label: '就绪', color: 'bg-status-success-muted text-status-success' },
  LEASED: { label: '已租用', color: 'bg-status-warning-muted text-status-warning' },
  IN_USE: { label: '使用中', color: 'bg-status-info-muted text-status-info' },
  CLEANING: { label: '清理中', color: 'bg-status-info-muted text-status-info' },
  CLEANED: { label: '已清理', color: 'bg-status-success-muted text-status-success' },
  FAILED: { label: '失败', color: 'bg-status-danger-muted text-status-danger' },
  ACTIVE: { label: '活跃', color: 'bg-status-success-muted text-status-success' },
  RELEASED: { label: '已释放', color: 'bg-status-info-muted text-status-info' },
}
