import { aitdeV2 } from './missions'

export interface SourceArtifact {
  id: number
  project_id: number
  source_type: string
  provider: string
  name: string
  uri: string
  content_hash: string
  version_label: string
  sensitivity: string
  parse_status: 'PENDING' | 'PARSING' | 'PARSED' | 'FAILED' | string
  metadata_json: string
  created_by: number
  created_at: string | null
  updated_at: string | null
  role?: string | null
  fragment_count: number
}

export interface SourceFragment {
  id: number
  artifact_id: number
  fragment_key: string
  title: string
  text: string
  location_json: string
  content_hash: string
  sequence: number
  created_at: string | null
}

export interface SourceAttachInput {
  source_type: 'REQUIREMENT' | 'OPENAPI' | 'MANUAL_NOTE'
  provider?: string
  requirement_doc_id?: number | null
  uri?: string | null
  name?: string | null
  content?: string | null
  role?: string
}

export function fetchMissionSources(missionId: number): Promise<SourceArtifact[]> {
  return aitdeV2.get(`/missions/${missionId}/sources`)
}

export function attachMissionSource(
  missionId: number,
  payload: SourceAttachInput,
): Promise<SourceArtifact> {
  return aitdeV2.post(`/missions/${missionId}/sources`, payload)
}

export function parseMissionSource(
  missionId: number,
  sourceId: number,
): Promise<{ artifact_id: number; parse_status: string; fragment_count: number }> {
  return aitdeV2.post(`/missions/${missionId}/sources/${sourceId}/parse`)
}

export function fetchSourceFragments(
  missionId: number,
  sourceId: number,
): Promise<SourceFragment[]> {
  return aitdeV2.get(`/missions/${missionId}/sources/${sourceId}/fragments`)
}

export const SOURCE_TYPE_LABELS: Record<string, string> = {
  REQUIREMENT: '需求文档',
  OPENAPI: 'OpenAPI',
  MANUAL_NOTE: '人工补充',
  WIKI: 'Wiki',
  PROTOTYPE: '原型',
  HISTORICAL_CASE: '历史用例',
  HISTORICAL_DEFECT: '历史缺陷',
}

export const PARSE_STATUS_LABELS: Record<string, { label: string; color: string }> = {
  PENDING: { label: '待解析', color: 'bg-muted text-muted-foreground' },
  PARSING: { label: '解析中', color: 'bg-status-info-muted text-status-info' },
  PARSED: { label: '已解析', color: 'bg-status-success-muted text-status-success' },
  FAILED: { label: '解析失败', color: 'bg-status-danger-muted text-status-danger' },
}
